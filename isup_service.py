# -*- coding: utf-8 -*-
import os
import platform
import queue
import threading
import traceback
from ctypes import (
    POINTER,
    byref,
    c_int,
    c_void_p,
    cast,
    create_string_buffer,
    memmove,
    sizeof,
    string_at,
)
from datetime import datetime

from alarm_ingest import persist_alarm
from HCISUPSDK import (
    AlarmInitCfgType,
    AlarmType,
    CmsInitCfgType,
    DEVICE_REGISTER_CB,
    EHomeMsgCallBack,
    LocalCfgType,
    MAX_DEVICE_ID_LEN,
    MAX_MASTER_KEY_LEN,
    NET_EHOME_ALARM_ISAPI_INFO,
    NET_EHOME_ALARM_ISAPI_PICDATA,
    NET_EHOME_ALARM_LISTEN_PARAM,
    NET_EHOME_ALARM_MSG,
    NET_EHOME_NOTICE_PICURL,
    NET_EHOME_AMS_ADDRESS,
    NET_EHOME_CMS_LISTEN_PARAM,
    NET_EHOME_DEV_REG_INFO_V12,
    NET_EHOME_DEV_SESSIONKEY,
    NET_EHOME_LOCAL_ACCESS_SECURITY,
    NET_EHOME_LOCAL_GENERAL_CFG,
    NET_EHOME_REGISTER_LISTEN_MODE,
    NET_EHOME_SERVER_INFO_V50,
    RegisterType,
    bytes_to_str,
    load_alarm_dll,
    load_cms_dll,
    _pick_ssl_dll_names,
)

ALARM_TYPE_LABELS = {
    AlarmType.EHOME_ISAPI_ALARM.value: "EHOME_ISAPI_ALARM",
    AlarmType.EHOME_ALARM.value: "EHOME_ALARM",
    AlarmType.EHOME_ALARM_NOTICE_PICURL.value: "EHOME_NOTICE_PICURL",
}


class IsupAlarmService:
    def __init__(self, config, storage, notifier=None):
        self.config = config
        self.storage = storage
        self.notifier = notifier
        self.running = False
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._worker = threading.Thread(target=self._process_queue, daemon=True)
        self._cms_dll = None
        self._alarm_dll = None
        self._cms_handle = -1
        self._ams_handles = []
        self._register_cb = None
        self._alarm_cb = None
        self._server_info = None
        self._user_devices = {}
        self._device_registry = {}
        isup = config.get("isup", {})
        self._platform_ip = isup.get("platform_ip", "127.0.0.1")
        self._ehome_keys = isup.get("ehome_keys", {})
        self._default_ehome_key = isup.get("default_ehome_key", "")
        self._device_auth = config.get("device_auth", {})
        self._status = {
            "state": "stopped",
            "protocol": "isup",
            "last_error": None,
            "started_at": None,
            "last_alarm_at": None,
            "registered_devices": 0,
            "device_ids": [],
        }

    @property
    def status(self):
        with self._lock:
            return dict(self._status)

    def _set_status(self, **kwargs):
        with self._lock:
            self._status.update(kwargs)

    def wait_until_ready(self, timeout=30):
        return self._ready.wait(timeout=timeout)

    def start(self):
        self.running = True
        self._worker.start()
        try:
            self._set_status(state="starting", last_error=None)
            self._init_sdk()
            self._set_status(
                state="running",
                started_at=datetime.now().isoformat(timespec="seconds"),
            )
            self._ready.set()
            print("[isup-service] ISUP CMS/AMS 已启动，等待设备注册并上报告警...")
            while self.running:
                threading.Event().wait(1)
        except Exception as exc:
            self._set_status(state="error", last_error=str(exc))
            print(f"[isup-service] 启动失败: {exc}")
            traceback.print_exc()
        finally:
            self._shutdown_sdk()

    def stop(self):
        self.running = False
        self._shutdown_sdk()
        self._set_status(state="stopped")

    def _lib_dir(self):
        return os.path.join(os.path.dirname(__file__), "lib")

    def _configure_openssl(self, dll, libeay_enum, ssleay_enum, set_cfg_name):
        lib_dir = self._lib_dir()
        crypto_name, ssl_name = _pick_ssl_dll_names(lib_dir)
        if platform.system().lower() == "windows":
            base = lib_dir.encode("gbk")
        else:
            base = lib_dir.encode("utf-8")
        set_cfg = getattr(dll, set_cfg_name)
        set_cfg.argtypes = [c_int, c_void_p]
        set_cfg.restype = c_int
        set_cfg(libeay_enum, create_string_buffer(base + b"\\" + crypto_name.encode("ascii")))
        set_cfg(ssleay_enum, create_string_buffer(base + b"\\" + ssl_name.encode("ascii")))

    def _init_sdk(self):
        lib_dir = self._lib_dir()
        log_dir = os.path.join(os.path.dirname(__file__), "SdkLog_Python")
        os.makedirs(log_dir, exist_ok=True)

        self._cms_dll = load_cms_dll()
        self._alarm_dll = load_alarm_dll()

        self._configure_openssl(
            self._cms_dll,
            CmsInitCfgType.NET_EHOME_CMS_INIT_CFG_LIBEAY_PATH.value,
            CmsInitCfgType.NET_EHOME_CMS_INIT_CFG_SSLEAY_PATH.value,
            "NET_ECMS_SetSDKInitCfg",
        )
        self._configure_openssl(
            self._alarm_dll,
            AlarmInitCfgType.NET_EHOME_EALARM_INIT_CFG_LIBEAY_PATH.value,
            AlarmInitCfgType.NET_EHOME_EALARM_INIT_CFG_SSLEAY_PATH.value,
            "NET_EALARM_SetSDKInitCfg",
        )

        if not self._cms_dll.NET_ECMS_Init():
            raise RuntimeError(f"NET_ECMS_Init 失败, err={self._cms_dll.NET_ECMS_GetLastError()}")
        if not self._alarm_dll.NET_EALARM_Init():
            raise RuntimeError(f"NET_EALARM_Init 失败, err={self._alarm_dll.NET_EALARM_GetLastError()}")

        self._cms_dll.NET_ECMS_SetLogToFile(3, log_dir.encode("utf-8"), 0)
        self._alarm_dll.NET_EALARM_SetLogToFile(3, log_dir.encode("utf-8"), 0)

        general_cfg = NET_EHOME_LOCAL_GENERAL_CFG()
        general_cfg.byAlarmPictureSeparate = (
            1 if self.config.get("isup", {}).get("alarm_picture_separate", True) else 0
        )
        self._alarm_dll.NET_EALARM_SetSDKLocalCfg(
            LocalCfgType.LOCAL_CFG_TYPE_GENERAL.value, byref(general_cfg)
        )

        listen_mode = NET_EHOME_REGISTER_LISTEN_MODE()
        listen_mode.dwSize = sizeof(listen_mode)
        listen_mode.dwRegisterListenMode = 0
        self._cms_dll.NET_ECMS_SetSDKLocalCfg(
            LocalCfgType.REGISTER_LISTEN_MODE.value, byref(listen_mode)
        )

        access_cfg = NET_EHOME_LOCAL_ACCESS_SECURITY()
        access_cfg.dwSize = sizeof(access_cfg)
        access_cfg.byAccessSecurity = 0  # 0=兼容模式，允许 ISUP5.0 接入
        self._cms_dll.NET_ECMS_SetSDKLocalCfg(
            LocalCfgType.ACTIVE_ACCESS_SECURITY.value, byref(access_cfg)
        )
        self._alarm_dll.NET_EALARM_SetSDKLocalCfg(
            LocalCfgType.ACTIVE_ACCESS_SECURITY.value, byref(access_cfg)
        )

        self._prepare_server_info()
        self._start_cms_listen()
        self._start_ams_listen()
        self._enable_cms_alarm_route()

    def _prepare_server_info(self):
        isup = self.config.get("isup", {})
        cms_port = int(isup.get("cms", {}).get("port", 7660))
        ams_port = int(isup.get("ams", {}).get("port", 7200))
        keep_alive = int(isup.get("keep_alive_sec", 15))
        timeout_count = int(isup.get("timeout_count", 6))
        alarm_keep_alive = int(isup.get("alarm_keep_alive_sec", 30))
        alarm_timeout = int(isup.get("alarm_timeout_count", 3))

        info = NET_EHOME_SERVER_INFO_V50()
        info.dwSize = sizeof(info)
        info.dwKeepAliveSec = keep_alive
        info.dwTimeOutCount = timeout_count
        info.dwAlarmKeepAliveSec = alarm_keep_alive
        info.dwAlarmTimeOutCount = alarm_timeout
        info.dwAlarmServerType = 1

        ip = self._platform_ip.encode("ascii")
        info.struTCPAlarmSever.szIP = ip
        info.struTCPAlarmSever.wPort = ams_port
        info.struUDPAlarmSever.szIP = ip
        info.struUDPAlarmSever.wPort = ams_port
        self._server_info = info
        self._cms_port = cms_port
        self._ams_port = ams_port

    def _start_alarm_listener(self, host, port, protocol_name, by_protocol, use_cms_port):
        listen_param = NET_EHOME_ALARM_LISTEN_PARAM()
        listen_param.struAddress.szIP = host.encode("ascii")
        listen_param.struAddress.wPort = port
        listen_param.fnMsgCb = self._alarm_cb
        listen_param.byProtocolType = by_protocol
        listen_param.byUseCmsPort = 1 if use_cms_port else 0
        listen_param.dwKeepAliveSec = int(self.config.get("isup", {}).get("alarm_keep_alive_sec", 30))
        listen_param.dwTimeOutCount = int(
            self.config.get("isup", {}).get("alarm_timeout_count", 3)
        )

        handle = self._alarm_dll.NET_EALARM_StartListen(byref(listen_param))
        if handle < 0:
            err = self._alarm_dll.NET_EALARM_GetLastError()
            label = f"{protocol_name}{'+CMS' if use_cms_port else ''}"
            raise RuntimeError(f"NET_EALARM_StartListen({label}) 失败, err={err}")
        self._ams_handles.append(handle)
        cms_note = "，复用 CMS 通道" if use_cms_port else ""
        print(f"[isup-service] AMS 监听: {host}:{port} ({protocol_name}){cms_note}")

    def _ams_route_endpoint(self):
        """CMS 告警回环地址须为具体 IP，且不能与 CMS 端口 7660 共用。"""
        isup = self.config.get("isup", {})
        ams_cfg = isup.get("ams", {})
        host = (
            ams_cfg.get("route_host")
            or isup.get("platform_ip")
            or "127.0.0.1"
        )
        port = int(ams_cfg.get("route_port") or ams_cfg.get("port", 7200))
        return host, port

    def _start_ams_listen(self):
        isup = self.config.get("isup", {})
        ams_cfg = isup.get("ams", {})
        host = ams_cfg.get("host", "0.0.0.0")
        port = int(ams_cfg.get("port", 7200))
        protocol = ams_cfg.get("protocol", "both").lower()
        use_cms_port = bool(ams_cfg.get("use_cms_port", True))

        self._alarm_cb = EHomeMsgCallBack(self._on_alarm_callback)

        protocols = []
        if protocol in ("tcp", "both"):
            protocols.append(("tcp", 0))
        if protocol in ("udp", "both"):
            protocols.append(("udp", 1))
        if not protocols:
            protocols.append(("tcp", 0))

        for proto_name, by_protocol in protocols:
            self._start_alarm_listener(host, port, proto_name, by_protocol, False)

        if use_cms_port:
            route_host, route_port = self._ams_route_endpoint()
            self._start_alarm_listener(route_host, route_port, "tcp", 0, True)

    def _enable_cms_alarm_route(self):
        isup = self.config.get("isup", {})
        ams_cfg = isup.get("ams", {})
        if not ams_cfg.get("use_cms_port", True):
            return
        route_host, route_port = self._ams_route_endpoint()

        ams_addr = NET_EHOME_AMS_ADDRESS()
        ams_addr.dwSize = sizeof(ams_addr)
        ams_addr.byEnable = 1
        ams_addr.struAddress.szIP = route_host.encode("ascii")
        ams_addr.struAddress.wPort = route_port

        if not self._cms_dll.NET_ECMS_SetSDKLocalCfg(
            LocalCfgType.AMS_ADDRESS.value, byref(ams_addr)
        ):
            err = self._cms_dll.NET_ECMS_GetLastError()
            print(
                f"[isup-service] 警告: CMS 告警路由未启用(err={err})，"
                f"仍可通过 AMS {self._platform_ip}:{self._ams_port} 接收告警"
            )
            return
        print(f"[isup-service] CMS 告警路由已启用 -> {route_host}:{route_port}")

    def _start_cms_listen(self):
        isup = self.config.get("isup", {})
        cms_cfg = isup.get("cms", {})
        host = cms_cfg.get("host", "0.0.0.0")
        port = int(cms_cfg.get("port", 7660))

        self._register_cb = DEVICE_REGISTER_CB(self._on_register_callback)
        listen_param = NET_EHOME_CMS_LISTEN_PARAM()
        listen_param.struAddress.szIP = host.encode("ascii")
        listen_param.struAddress.wPort = port
        listen_param.fnCB = self._register_cb
        listen_param.dwKeepAliveSec = int(isup.get("keep_alive_sec", 15))
        listen_param.dwTimeOutCount = int(isup.get("timeout_count", 6))

        handle = self._cms_dll.NET_ECMS_StartListen(byref(listen_param))
        if handle < 0:
            raise RuntimeError(
                f"NET_ECMS_StartListen 失败, err={self._cms_dll.NET_ECMS_GetLastError()}"
            )
        self._cms_handle = handle
        print(f"[isup-service] CMS 监听: {host}:{port}，设备接入 IP={self._platform_ip}")

    def _shutdown_sdk(self):
        if self._alarm_dll:
            for handle in self._ams_handles:
                if handle >= 0:
                    self._alarm_dll.NET_EALARM_StopListen(handle)
            self._ams_handles = []
        if self._cms_dll:
            ams_addr = NET_EHOME_AMS_ADDRESS()
            ams_addr.dwSize = sizeof(ams_addr)
            ams_addr.byEnable = 0
            self._cms_dll.NET_ECMS_SetSDKLocalCfg(
                LocalCfgType.AMS_ADDRESS.value, byref(ams_addr)
            )
        if self._cms_dll and self._cms_handle >= 0:
            self._cms_dll.NET_ECMS_StopListen(self._cms_handle)
            self._cms_handle = -1
        if self._alarm_dll:
            self._alarm_dll.NET_EALARM_Fini()
        if self._cms_dll:
            self._cms_dll.NET_ECMS_Fini()
        self._cms_dll = None
        self._alarm_dll = None

    def _lookup_ehome_key(self, device_id):
        if device_id in self._ehome_keys:
            return self._ehome_keys[device_id]
        return self._default_ehome_key

    def _write_key_to_buffer(self, in_buffer, in_len, key):
        if not in_buffer or not key:
            return
        key_buf = create_string_buffer(key.encode("ascii")[:32])
        copy_len = min(32, in_len, len(key_buf.raw))
        memmove(in_buffer, key_buf, copy_len)

    def _on_register_callback(
        self, user_id, data_type, out_buffer, out_len, in_buffer, in_len, user
    ):
        try:
            if data_type not in (
                RegisterType.ENUM_DEV_DAS_PINGREO.value,
                RegisterType.ENUM_DEV_SESSIONKEY.value,
            ):
                print(f"[isup-service] 注册回调 type={data_type}, user_id={user_id}")

            if data_type == RegisterType.ENUM_DEV_ON.value:
                if not in_buffer or not out_buffer:
                    return False
                dev_info = cast(out_buffer, POINTER(NET_EHOME_DEV_REG_INFO_V12)).contents
                device_id = bytes_to_str(bytes(dev_info.struRegInfo.byDeviceID))
                serial = bytes_to_str(bytes(dev_info.struRegInfo.sDeviceSerial))
                dev_ip = bytes_to_str(dev_info.struRegInfo.struDevAdd.szIP)

                server_info = NET_EHOME_SERVER_INFO_V50()
                memmove(byref(server_info), byref(self._server_info), sizeof(server_info))
                memmove(in_buffer, byref(server_info), sizeof(server_info))

                with self._lock:
                    self._user_devices[user_id] = device_id
                    self._device_registry[device_id] = {
                        "device_id": device_id,
                        "serial": serial,
                        "device_ip": dev_ip,
                        "user_id": user_id,
                    }
                    ids = sorted(self._device_registry.keys())
                    self._status["device_ids"] = ids
                    self._status["registered_devices"] = len(ids)

                print(
                    f"[isup-service] 设备上线 id={device_id}, serial={serial}, ip={dev_ip}, "
                    f"告警服务器={self._platform_ip}:{self._ams_port}(TCP/UDP)"
                )
                return True

            if data_type == RegisterType.ENUM_DEV_OFF.value:
                with self._lock:
                    device_id = self._user_devices.pop(user_id, None)
                    if device_id:
                        self._device_registry.pop(device_id, None)
                    self._status["device_ids"] = sorted(self._device_registry.keys())
                    self._status["registered_devices"] = len(self._device_registry)
                print(f"[isup-service] 设备下线 user_id={user_id}, device_id={device_id}")
                return True

            if data_type == RegisterType.ENUM_DEV_AUTH.value:
                if not out_buffer or not in_buffer:
                    return False
                dev_info = cast(out_buffer, POINTER(NET_EHOME_DEV_REG_INFO_V12)).contents
                device_id = bytes_to_str(bytes(dev_info.struRegInfo.byDeviceID))
                key = self._lookup_ehome_key(device_id)
                print(f"[isup-service] 设备认证 id={device_id}, key_set={bool(key)}")
                self._write_key_to_buffer(in_buffer, in_len, key)
                return True

            if data_type == RegisterType.ENUM_DEV_DAS_REQ.value:
                if not in_buffer:
                    return False
                das_json = (
                    f'{{"Type":"DAS","DasInfo":{{"Address":"{self._platform_ip}",'
                    f'"Domain":"local","ServerID":"das_{self._platform_ip}_{self._cms_port}",'
                    f'"Port":{self._cms_port},"UdpPort":{self._cms_port}}}}}'
                )
                payload = das_json.encode("ascii")
                if in_len < len(payload) + 1:
                    print("[isup-service] DAS 响应缓冲区不足")
                    return False
                memmove(in_buffer, payload, len(payload))
                print(f"[isup-service] DAS 重定向 -> {self._platform_ip}:{self._cms_port}")
                return True

            if data_type == RegisterType.ENUM_DEV_DAS_EHOMEKEY_ERROR.value:
                if out_buffer:
                    dev_info = cast(out_buffer, POINTER(NET_EHOME_DEV_REG_INFO_V12)).contents
                    device_id = bytes_to_str(bytes(dev_info.struRegInfo.byDeviceID))
                    print(f"[isup-service] 加密密钥错误 device_id={device_id}")
                return True

            if data_type == RegisterType.ENUM_DEV_SESSIONKEY.value:
                if not out_buffer:
                    return True
                dev_info = cast(out_buffer, POINTER(NET_EHOME_DEV_REG_INFO_V12)).contents
                device_id = bytes_to_str(bytes(dev_info.struRegInfo.byDeviceID))
                session = NET_EHOME_DEV_SESSIONKEY()
                memmove(session.sDeviceID, dev_info.struRegInfo.byDeviceID, MAX_DEVICE_ID_LEN)
                memmove(session.sSessionKey, dev_info.struRegInfo.bySessionKey, MAX_MASTER_KEY_LEN)
                self._cms_dll.NET_ECMS_SetDeviceSessionKey(byref(session))
                self._alarm_dll.NET_EALARM_SetDeviceSessionKey(byref(session))
                print(f"[isup-service] 会话密钥已同步 device_id={device_id}")
                return True
        except Exception as exc:
            print(f"[isup-service] 注册回调异常: {exc}")
        return True

    def _extract_isapi_pictures(self, info):
        pics = []
        pic_num = info.byPicturesNumber
        if not pic_num or not info.pPicPackData:
            return pics
        pic_array_type = NET_EHOME_ALARM_ISAPI_PICDATA * pic_num
        pic_array = cast(info.pPicPackData, pic_array_type)
        for idx in range(pic_num):
            pic_len = pic_array[idx].dwPicLen
            pic_ptr = pic_array[idx].pPicData
            if pic_len and pic_ptr:
                pics.append(string_at(pic_ptr, pic_len))
        return pics

    def _read_http_url(self, msg):
        if not msg.pHttpUrl or not msg.dwHttpUrlLen:
            return ""
        return string_at(msg.pHttpUrl, msg.dwHttpUrlLen).decode("utf-8", errors="ignore").strip()

    def _on_alarm_callback(self, handle, alarm_msg, user):
        try:
            msg = alarm_msg.contents
            alarm_type = msg.dwAlarmType
            http_url = self._read_http_url(msg)
            if http_url:
                alarm_type = AlarmType.EHOME_ISAPI_ALARM.value
            label = ALARM_TYPE_LABELS.get(alarm_type, f"EHOME_{alarm_type}")
            print(
                f"[isup-service] 收到告警 type={alarm_type} ({label}), "
                f"info_len={msg.dwAlarmInfoLen}, xml_len={msg.dwXmlBufLen}, "
                f"http_url={'yes' if http_url else 'no'}"
            )

            payload = {
                "alarm_type": alarm_type,
                "command_label": label,
                "serial": bytes_to_str(msg.sSerialNumber),
                "alarm_info_len": msg.dwAlarmInfoLen,
                "xml_len": msg.dwXmlBufLen,
                "remote_urls": [http_url] if http_url else [],
                "pictures": [],
                "raw_bytes": b"",
            }

            if alarm_type == AlarmType.EHOME_ISAPI_ALARM.value and msg.pAlarmInfo:
                info = cast(msg.pAlarmInfo, POINTER(NET_EHOME_ALARM_ISAPI_INFO)).contents
                if info.dwAlarmDataLen and info.pAlarmData:
                    payload["raw_bytes"] = string_at(info.pAlarmData, info.dwAlarmDataLen)
                payload["pictures"] = self._extract_isapi_pictures(info)
            elif alarm_type == AlarmType.EHOME_ALARM_NOTICE_PICURL.value and msg.pAlarmInfo:
                notice = cast(msg.pAlarmInfo, POINTER(NET_EHOME_NOTICE_PICURL)).contents
                pic_url = bytes_to_str(notice.byPicUrl)
                if pic_url:
                    payload["remote_urls"].append(pic_url)
                payload["command_label"] = "EHOME_NOTICE_PICURL"
                payload["raw_bytes"] = (
                    f"<NoticePicUrl><picUrl>{pic_url}</picUrl>"
                    f"<alarmChan>{notice.dwAlarmChan}</alarmChan></NoticePicUrl>"
                ).encode("utf-8")
            elif msg.pAlarmInfo and msg.dwAlarmInfoLen:
                payload["raw_bytes"] = string_at(msg.pAlarmInfo, msg.dwAlarmInfoLen)
            elif msg.pXmlBuf and msg.dwXmlBufLen:
                payload["raw_bytes"] = string_at(msg.pXmlBuf, msg.dwXmlBufLen)

            print(
                f"[isup-service] 告警载荷 embedded_pics={len(payload['pictures'])}, "
                f"remote_urls={len(payload['remote_urls'])}"
            )
            self._queue.put_nowait(payload)
            self._set_status(last_alarm_at=datetime.now().isoformat(timespec="seconds"))
        except Exception as exc:
            print(f"[isup-service] 告警回调异常: {exc}")
            traceback.print_exc()
        return True

    def _process_queue(self):
        while self.running or not self._queue.empty():
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._persist_alarm(item)
            except Exception as exc:
                print(f"[isup-service] 告警入库异常: {exc}")
                traceback.print_exc()

    def _persist_alarm(self, item):
        raw_bytes = item.get("raw_bytes") or b""
        device_serial = item.get("serial") or "isup"
        device_ip = self._platform_ip
        with self._lock:
            for info in self._device_registry.values():
                if info.get("serial") == device_serial:
                    device_ip = info.get("device_ip") or device_ip
                    break

        persist_alarm(
            self.storage,
            self.notifier,
            self.config,
            raw_bytes,
            command_label=item.get("command_label", "EHOME_ALARM"),
            device_serial=device_serial,
            device_ip=device_ip,
            embedded_pictures=item.get("pictures") or [],
            remote_urls=item.get("remote_urls") or [],
            device_auth=self._device_auth,
        )
