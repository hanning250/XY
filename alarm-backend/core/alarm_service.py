# -*- coding: utf-8 -*-
"""ISUP（EHome）报警接收服务。

架构与老的 NET SDK 完全相反：

    NET ： 服务器 --登录/布防--> 设备        （服务器是客户端）
    ISUP： 设备 --注册/上报-->  服务器        （服务器是服务端）

流程：
    1. NET_ECMS_Init / NET_EALARM_Init
    2. NET_ECMS_StartListen (注册端口)   ← 设备连上来，回调报「设备上线」
    3. NET_EALARM_StartListen (报警端口) ← 设备推报警 + 图片
    4. 报警回调里 **只做字节拷贝 + 入队**，立刻返回
    5. worker 线程消费队列：存图片 → 解析 JSON → 入库 → WebSocket 推送

⚠ 为什么必须有队列：
    SDK 头文件明确写了「严禁在报警回调中调用 HCISUPSDK 外部接口」，
    且「耗时不宜超过 10ms」。老代码直接在回调里写文件 + 写 SQLite + 发
    WebSocket，在 ISUP 下会堵死 SDK 内部线程甚至崩溃。
"""

import json
import os
import queue
import threading
import time
import traceback
from collections import OrderedDict
from ctypes import POINTER, cast, string_at
from datetime import datetime

from common.event_parser import (
    is_aiop_ppe_related,
    is_ppe_related,
    looks_like_aiop_json,
    make_picture_name,
    parse_aiop_data,
    parse_isapi_payload,
)
from core.hcisup import (
    ALARM_TYPE_LABELS,
    DEVICE_REGISTER_CB,
    EHOME_ISAPI_ALARM,
    EHomeMsgCallBack,
    ENUM_DEV_AUTH,
    ENUM_DEV_DAS_EHOMEKEY_ERROR,
    ENUM_DEV_DAS_PINGREO,
    ENUM_DEV_OFF,
    ENUM_DEV_ON,
    ISUPSDK,
    LPNET_EHOME_ALARM_ISAPI_INFO,
    NET_EHOME_ALARM_ISAPI_PICDATA,
    PROTOCOL_MQTT,
    PROTOCOL_TCP,
    PROTOCOL_UDP,
    REGISTER_TYPE_LABELS,
    pick_ssl_dll_names,
    LIB_DIR,
)
from common.alarm_view import notify_alarm

# 队列上限：防止设备疯狂上报把内存撑爆。满了就丢最旧的并计数。
MAX_PENDING_ALARMS = 2000
JPEG_MAGIC = b"\xff\xd8\xff"


class ISUPAlarmService:
    """设备主动注册 + 报警接收。"""

    def __init__(self, config, storage, notifier=None, register_callback=None,
                 alarm_callback=None):
        self.config = config
        self.storage = storage
        self.notifier = notifier

        self.sdk = None
        self.running = False
        self._ready = threading.Event()
        self._lock = threading.Lock()

        # 回调 → worker 的队列
        self._queue = queue.Queue(maxsize=MAX_PENDING_ALARMS)
        self._worker = None

        # 设备注册表：login_id -> 设备信息
        self._devices = OrderedDict()

        self._status = {
            "state": "stopped",
            "last_error": None,
            "last_connected_at": None,
            "last_alarm_at": None,
            "reconnect_count": 0,
            "alarm_mode": "isup",
            "listen_ip": None,
            "register_port": None,
            "alarm_port": None,
            "protocol": None,
            "devices": [],
            "devices_online": 0,
            "dropped_alarms": 0,
            "received_alarms": 0,
        }

        # register_callback / alarm_callback 用于现场诊断时插一层日志；
        # 默认走本类的实现。回调对象必须长期持有，否则会被 GC 回收导致崩溃。
        register_handler = register_callback or self._on_device_register
        alarm_handler = alarm_callback or self._on_alarm_msg
        self._register_cb = DEVICE_REGISTER_CB(register_handler)
        self._alarm_cb = EHomeMsgCallBack(alarm_handler)

        # 消费线程随服务对象一起起来，保证「回调入队后一定有人处理」
        self._worker = threading.Thread(
            target=self._consume_loop, name="isup-worker", daemon=True
        )
        self._worker.start()

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    @property
    def status(self):
        with self._lock:
            data = dict(self._status)
            data["devices"] = list(self._devices.values())
            return data

    def _set_status(self, **kwargs):
        with self._lock:
            self._status.update(kwargs)

    def _bump(self, key, delta=1):
        with self._lock:
            self._status[key] = self._status.get(key, 0) + delta

    def wait_until_ready(self, timeout=30):
        return self._ready.wait(timeout=timeout)

    # ------------------------------------------------------------------
    # 启停
    # ------------------------------------------------------------------
    def start(self):
        self.running = True
        reconnect_cfg = self.config.get("reconnect", {})
        interval = int(reconnect_cfg.get("interval_seconds", 10))
        max_retries = reconnect_cfg.get("max_retries", 0)

        attempt = 0
        while self.running:
            try:
                self._start_once()
                self._set_status(
                    state="listening",
                    last_error=None,
                    last_connected_at=datetime.now().isoformat(timespec="seconds"),
                    reconnect_count=attempt,
                )
                self._ready.set()
                while self.running:
                    time.sleep(1)
            except Exception as exc:
                attempt += 1
                err = f"{type(exc).__name__}: {exc}"
                self._set_status(state="error", last_error=err, reconnect_count=attempt)
                print(f"[isup] 启动失败: {err}")
                traceback.print_exc()
                self._safe_fini()
                if max_retries and attempt >= int(max_retries):
                    self._set_status(state="stopped")
                    print(f"[isup] 已达最大重试次数 ({max_retries})，停止")
                    break
                if not self.running:
                    break
                print(f"[isup] {interval}s 后重试...")
                time.sleep(interval)

    def stop(self):
        self.running = False
        self._ready.clear()
        self._safe_fini()
        self._set_status(state="stopped")

    def stop_and_join(self, timeout=5):
        """停止监听，并把队列里剩下的事件处理完再退出 worker。"""
        self.stop()
        if self._worker is not None and self._worker.is_alive():
            try:
                self._queue.put_nowait(None)  # 哨兵：worker 处理完剩余后退出
            except queue.Full:
                pass
            self._worker.join(timeout=timeout)

    def _safe_fini(self):
        if self.sdk is not None:
            try:
                self.sdk.stop_listen()
                self.sdk.fini()
            except Exception:
                pass
            self.sdk = None

    def _start_once(self):
        isup_cfg = self.config.get("isup", {})
        listen_ip = isup_cfg.get("listen_ip", "0.0.0.0")
        register_port = int(isup_cfg.get("register_port", 7660))
        alarm_port = int(isup_cfg.get("alarm_port", 7661))

        protocol_name = str(isup_cfg.get("protocol", "tcp")).lower()
        protocol_type = {"tcp": PROTOCOL_TCP, "udp": PROTOCOL_UDP, "mqtt": PROTOCOL_MQTT}.get(
            protocol_name, PROTOCOL_TCP
        )

        if register_port == alarm_port and not isup_cfg.get("reuse_cms_port", False):
            raise ValueError(
                f"注册端口和报警端口不能相同 ({register_port})；"
                "若要复用请设置 isup.reuse_cms_port=true"
            )

        # 消费线程在 __init__ 里已启动，这里只兜底（比如线程意外退出）
        if self._worker is None or not self._worker.is_alive():
            self._worker = threading.Thread(
                target=self._consume_loop, name="isup-worker", daemon=True
            )
            self._worker.start()

        print(f"[isup] 初始化 SDK，运行库目录: {LIB_DIR}")
        self.sdk = ISUPSDK()
        # 打印一下版本，便于现场确认
        try:
            versions = self.sdk.get_versions()
            print(f"[isup] SDK 版本: CMS={versions['cms']} Alarm={versions['alarm']}")
        except Exception:
            pass

        libeay, ssleay = pick_ssl_dll_names(LIB_DIR)
        self.sdk.set_openssl_paths(libeay, ssleay)
        self.sdk.init()

        # 接入安全模式：设备是 ISUP 4.0/5.0 用 2；不确定时用 0 先接通
        access_mode = int(isup_cfg.get("access_security", 0))
        try:
            self.sdk.set_access_security(access_mode)
        except Exception as exc:
            print(f"[isup] 设置接入安全模式失败（不致命）: {exc}")

        try:
            self.sdk.set_register_listen_mode(
                int(isup_cfg.get("register_listen_mode", 0))
            )
        except Exception as exc:
            print(f"[isup] 设置注册监听模式失败（不致命）: {exc}")

        keep_alive = int(isup_cfg.get("keep_alive_sec", 30))
        timeout_count = int(isup_cfg.get("timeout_count", 3))

        print(f"[isup] 开启设备注册监听 {listen_ip}:{register_port}")
        self.sdk.start_cms_listen(
            listen_ip,
            register_port,
            self._register_cb,
            None,
            keep_alive_sec=keep_alive,
            timeout_count=timeout_count,
        )

        print(
            f"[isup] 开启报警监听 {listen_ip}:{alarm_port} (协议 {protocol_name.upper()})"
        )
        self.sdk.start_alarm_listen(
            listen_ip,
            alarm_port,
            self._alarm_cb,
            None,
            protocol_type=protocol_type,
            use_cms_port=bool(isup_cfg.get("reuse_cms_port", False)),
            use_thread_pool=bool(isup_cfg.get("use_thread_pool", False)),
            keep_alive_sec=keep_alive,
            timeout_count=timeout_count,
        )

        self._set_status(
            listen_ip=listen_ip,
            register_port=register_port,
            alarm_port=alarm_port,
            protocol=protocol_name,
        )

    # ------------------------------------------------------------------
    # 回调 —— 只做拷贝和入队，绝不碰 DB / 文件 / 网络
    # ------------------------------------------------------------------
    def _on_device_register(
        self, login_id, data_type, p_out_buffer, out_len, p_in_buffer, in_len, user
    ):
        try:
            label = REGISTER_TYPE_LABELS.get(data_type, f"type_{data_type}")
            info = {"login_id": int(login_id), "type": int(data_type), "label": label}

            if data_type == ENUM_DEV_ON and p_out_buffer:
                self._read_reg_info(p_out_buffer, info)

            if data_type in (
                ENUM_DEV_ON,
                ENUM_DEV_OFF,
                ENUM_DEV_AUTH,
                ENUM_DEV_DAS_EHOMEKEY_ERROR,
                ENUM_DEV_DAS_PINGREO,
            ):
                self._enqueue({"kind": "register", "info": info})
                # 回调里只打一行日志，不做别的
                print(
                    f"[isup] 设备事件: {label} loginID={login_id} "
                    f"devID={info.get('device_id', '-')}"
                )
        except Exception as exc:
            # 回调里绝对不能抛异常出去，否则会打断 SDK 内部线程
            print(f"[isup] 注册回调异常: {type(exc).__name__}: {exc}")
        return True

    def _read_reg_info(self, p_out_buffer, info):
        """从 NET_EHOME_DEV_REG_INFO_V12 里拷出设备标识（只用 ctypes，不调 SDK 接口）。"""
        from core.hcisup import LPNET_EHOME_DEV_REG_INFO_V12

        try:
            reg = cast(p_out_buffer, LPNET_EHOME_DEV_REG_INFO_V12).contents
            raw = bytes(reg.struRegInfo.byDeviceID)
            info["device_id"] = raw.split(b"\x00", 1)[0].decode("utf-8", "ignore")
            info["serial"] = bytes(reg.struRegInfo.sDeviceSerial).split(b"\x00", 1)[0].decode(
                "utf-8", "ignore"
            )
            info["device_name"] = bytes(reg.sDevName).split(b"\x00", 1)[0].decode(
                "utf-8", "ignore"
            )
            info["firmware"] = bytes(reg.struRegInfo.byFirmwareVersion).split(b"\x00", 1)[
                0
            ].decode("utf-8", "ignore")
            info["protocol_version"] = bytes(
                reg.struRegInfo.byDevProtocolVersion
            ).split(b"\x00", 1)[0].decode("utf-8", "ignore")
            info["device_ip"] = bytes(reg.struRegInfo.struDevAdd.szIP).split(b"\x00", 1)[
                0
            ].decode("utf-8", "ignore")
            info["device_port"] = int(reg.struRegInfo.struDevAdd.wPort)
            info["full_serial"] = bytes(reg.byDeviceFullSerial).split(b"\x00", 1)[
                0
            ].decode("utf-8", "ignore")
        except Exception as exc:
            info["parse_error"] = f"{type(exc).__name__}: {exc}"

    def _on_alarm_msg(self, handle, msg_ptr, user):
        """报警回调：只把数据拷出来入队，立刻返回。"""
        try:
            self._bump("received_alarms")
            msg = msg_ptr.contents
            alarm_type = int(msg.dwAlarmType)
            payload = {
                "kind": "alarm",
                "alarm_type": alarm_type,
                "alarm_type_label": ALARM_TYPE_LABELS.get(
                    alarm_type, f"type_{alarm_type}"
                ),
                "serial": bytes(msg.sSerialNumber).split(b"\x00", 1)[0].decode(
                    "utf-8", "ignore"
                ),
                "received_at": datetime.now().isoformat(timespec="seconds"),
                "isapi": None,
                "text": None,
                "url": None,
            }

            # ISUP4.0「报警与图片不分离」时图片走 URL
            if msg.pHttpUrl and msg.dwHttpUrlLen:
                payload["url"] = string_at(
                    msg.pHttpUrl, int(msg.dwHttpUrlLen)
                ).split(b"\x00", 1)[0].decode("utf-8", "ignore")

            if msg.pXmlBuf and msg.dwXmlBufLen:
                payload["text"] = string_at(msg.pXmlBuf, int(msg.dwXmlBufLen)).decode(
                    "utf-8", "ignore"
                )

            if alarm_type == EHOME_ISAPI_ALARM and msg.pAlarmInfo:
                payload["isapi"] = self._copy_isapi(msg.pAlarmInfo)

            self._enqueue(payload)
        except Exception as exc:
            # 同上：回调里不能让异常逃出去
            print(f"[isup] 报警回调异常: {type(exc).__name__}: {exc}")
        return True

    @staticmethod
    def _copy_isapi(p_alarm_info):
        """把 NET_EHOME_ALARM_ISAPI_INFO 及其图片拷成纯 Python 数据。

        这一步是回调里唯一的重活，但只是 memcpy，微秒级，满足 10ms 约束。
        """
        info = cast(p_alarm_info, LPNET_EHOME_ALARM_ISAPI_INFO).contents
        result = {
            "data_type": int(info.byDataType),
            "pictures_number": int(info.byPicturesNumber),
            "alarm_data": b"",
            "pictures": [],
        }

        if info.pAlarmData and info.dwAlarmDataLen:
            result["alarm_data"] = string_at(
                info.pAlarmData, int(info.dwAlarmDataLen)
            )

        if info.pPicPackData and info.byPicturesNumber:
            count = int(info.byPicturesNumber)
            struct_array = cast(
                info.pPicPackData, POINTER(NET_EHOME_ALARM_ISAPI_PICDATA * count)
            ).contents
            for index in range(count):
                item = struct_array[index]
                length = int(item.dwPicLen)
                if not length or not item.pPicData:
                    continue
                result["pictures"].append(
                    {
                        "index": index,
                        "length": length,
                        "filename": bytes(item.szFilename)
                        .split(b"\x00", 1)[0]
                        .decode("utf-8", "ignore"),
                        "data": string_at(item.pPicData, length),
                    }
                )
        return result

    def _enqueue(self, item):
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            # 丢最旧的，保最新的
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(item)
            except Exception:
                pass
            self._bump("dropped_alarms")
            print("[isup] 队列已满，丢弃最旧的一条告警")

    # ------------------------------------------------------------------
    # worker 线程：真正干活的地方
    # ------------------------------------------------------------------
    def _consume_loop(self):
        """worker：从队列取事件并处理。

        队列是 FIFO，哨兵 None 排在所有已入队事件之后，
        所以收到哨兵时前面的事件都已经处理完了。
        """
        while True:
            try:
                item = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            if item is None:
                return

            try:
                if item["kind"] == "register":
                    self._handle_register(item["info"])
                else:
                    self._handle_alarm(item)
            except Exception as exc:
                print(f"[isup] 处理失败: {type(exc).__name__}: {exc}")
                traceback.print_exc()
            finally:
                self._queue.task_done()

    def _handle_register(self, info):
        login_id = info["login_id"]
        dtype = info["type"]
        now = datetime.now().isoformat(timespec="seconds")

        if dtype == ENUM_DEV_ON:
            info["state"] = "online"
            info["online_at"] = now
            self._devices[login_id] = info
            print(
                f"[isup] ✓ 设备上线: id={info.get('device_id')} "
                f"sn={info.get('serial')} ip={info.get('device_ip')} "
                f"ver={info.get('protocol_version')}"
            )
        elif dtype == ENUM_DEV_OFF:
            device = self._devices.get(login_id) or {"login_id": login_id}
            device["state"] = "offline"
            device["offline_at"] = now
            self._devices[login_id] = device
            print(f"[isup] ✗ 设备下线: id={device.get('device_id')}")
        elif dtype == ENUM_DEV_DAS_EHOMEKEY_ERROR:
            self._set_status(
                last_error="设备密钥校验失败（EHOMEKEY）——检查设备侧 ISUP 密钥配置"
            )
            print("[isup] ✗ 设备密钥校验失败，请核对设备上的 ISUP 密钥")
        else:
            # 认证 / 心跳 / 重注册等：只记时间戳，不改变在线状态
            device = self._devices.get(login_id)
            if device is not None:
                device["last_event"] = now
                device["last_event_type"] = REGISTER_TYPE_LABELS.get(
                    dtype, f"type_{dtype}"
                )
                self._devices[login_id] = device

        self._set_status(
            devices_online=sum(
                1 for d in self._devices.values() if d.get("state") == "online"
            )
        )

    def _handle_alarm(self, item):
        alarm_type = item["alarm_type"]
        label = item["alarm_type_label"]
        serial = item.get("serial") or ""
        device = self._find_device(serial)
        device_id = device.get("device_id") or serial or "unknown"
        device_ip = device.get("device_ip") or "-"

        print(
            f"[isup] 收到报警 type={alarm_type}({label}) from {device_id} ip={device_ip}"
        )

        if alarm_type != EHOME_ISAPI_ALARM:
            # 非 ISAPI 报警：先按原始内容落库，方便后续补解析
            detail = {
                "alarm_type": alarm_type,
                "alarm_type_label": label,
                "device_id": device_id,
                "serial": serial,
                "received_at": item.get("received_at"),
                "text": (item.get("text") or "")[:2000],
                "url": item.get("url"),
            }
            raw = item.get("text") or item.get("url") or f"未解析的ISUP报警: {label}"
            alarm_id = self.storage.save_alarm(
                device_ip=device_ip,
                device_serial=device_id,
                command_type=label,
                event_type=f"isup_{label.lower()}",
                channel_no=None,
                event_time=datetime.now().isoformat(timespec="seconds"),
                raw_payload=raw,
                picture_paths=[],
                is_ppe_related=False,
                event_detail=json.dumps(detail, ensure_ascii=False),
            )
            notify_alarm(self.notifier, self.storage, alarm_id)
            self._set_status(last_alarm_at=datetime.now().isoformat(timespec="seconds"))
            return

        self._handle_isapi_alarm(item, device_id, device_ip, serial, label)

    def _find_device(self, serial):
        if not serial:
            return {}
        for device in self._devices.values():
            if device.get("serial") == serial:
                return device
        return {}

    def _handle_isapi_alarm(self, item, device_id, device_ip, serial, label):
        isapi = item.get("isapi") or {}
        alarm_data = isapi.get("alarm_data") or b""
        data_type = isapi.get("data_type")

        # 1) 解析报警 JSON / XML（复用 event_parser）
        parsed = parse_isapi_payload(alarm_data)
        event_text = parsed["raw_text"] or item.get("text") or ""

        # 1b) 设备若下发 AI 开放平台的算法结果（targets/rect/confidence），一并解析
        aiop = {}
        if looks_like_aiop_json(alarm_data):
            aiop = parse_aiop_data(
                alarm_data, self.config.get("aiop_type_labels")
            )["aiop"]

        # 2) 保存图片 —— ISUP 的 pPicData 是真实指针，直接拿
        picture_paths = []
        picture_notes = []
        for picture in isapi.get("pictures", []):
            data = picture["data"]
            if not data:
                continue
            pic_name = make_picture_name(f"isup_ch{picture['index']}")
            pic_path = os.path.join(self.storage.picture_dir, pic_name)
            with open(pic_path, "wb") as fp:
                fp.write(data)
            picture_paths.append(pic_path)
            if not data.startswith(JPEG_MAGIC):
                note = f"图片{picture['index']} JPEG头不匹配: {data[:16].hex()}"
                picture_notes.append(note)
                print(f"[isup] 警告: {note}")

        if item.get("url"):
            picture_notes.append(f"设备返回图片URL(未下载): {item['url']}")

        # 3) 事件类型与 PPE 判定：优先用算法标签，其次用 ISAPI 的 eventType
        event_type = (
            aiop.get("label")
            or (f"aiop_type_{aiop['type']}" if aiop.get("type") is not None else None)
            or parsed["event_type"]
            or f"isup_{label.lower()}"
        )
        keywords = self.config.get("event_filter_keywords", [])
        ppe_flag = (
            is_aiop_ppe_related(aiop, keywords)
            if aiop.get("parsed")
            else False
        ) or is_ppe_related(event_type, event_text, keywords, parsed=parsed)

        # 4) 原始 JSON 落盘备查
        aiop_json_path = None
        if event_text:
            json_name = make_picture_name("isup").replace(".jpg", ".json")
            aiop_json_path = os.path.join(self.storage.picture_dir, json_name)
            with open(aiop_json_path, "w", encoding="utf-8") as fp:
                fp.write(event_text)

        detail = {
            "alarm_type": item["alarm_type"],
            "alarm_type_label": label,
            "device_id": device_id,
            "serial": serial,
            "device_ip": device_ip,
            "alarm_data_type": data_type,  # 1-xml 2-json
            "pictures_number": isapi.get("pictures_number"),
            "picture_notes": picture_notes,
            "aiop_json_path": aiop_json_path,
            "url": item.get("url"),
            "received_at": item.get("received_at"),
            "aiop": aiop or None,
        }

        # analysis 里放结构化结果：AIOP 优先，否则放 ISAPI 字段
        analysis = aiop if aiop.get("parsed") else parsed

        alarm_id = self.storage.save_alarm(
            device_ip=device_ip,
            device_serial=device_id,
            command_type=label,
            event_type=event_type,
            channel_no=parsed["channel_no"],
            event_time=parsed["event_time"]
            or datetime.now().isoformat(timespec="seconds"),
            raw_payload=event_text,
            picture_paths=picture_paths,
            is_ppe_related=ppe_flag,
            analysis=json.dumps(analysis, ensure_ascii=False),
            event_detail=json.dumps(detail, ensure_ascii=False),
        )
        notify_alarm(self.notifier, self.storage, alarm_id)
        self._set_status(last_alarm_at=datetime.now().isoformat(timespec="seconds"))
        print(
            f"[isup] ISAPI报警入库 id={alarm_id} type={event_type} "
            f"channel={parsed['channel_no']} pics={len(picture_paths)} "
            f"conf={aiop.get('confidence')} ppe={ppe_flag}"
        )
