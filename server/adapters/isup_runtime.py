# -*- coding: utf-8 -*-
"""★ ISUP 运行时：驱动现有 SDK 类，并把回调桥接到事件总线。

现有代码的约束（docs §1.2）：
  · glo 是进程级全局 dict
  · 回调在 SDK 自己的 C 线程里执行，绝不能做耗时操作或 await
  · cmsClass/amsClass/ssClass 负责监听，smsClass 负责取流（本方案不主动取流）

因此这里的做法是：
  1. 包装现有回调函数（不改 src/ 里的代码），在回调里只做
     「取字节 → bus.emit_from_thread(...)」，立即返回 True
  2. 用配置注入的 ISUPKey / 端口替代原 ConfRead 的 cwd 相对路径读取
"""

from __future__ import annotations

import ctypes
import logging
from datetime import datetime
from typing import Any

from server.adapters.sdk_paths import ensure_src_importable, sdk_available
from server.config import get_isup_conf, get_settings
from server.services.bus import bus

logger = logging.getLogger(__name__)

# 累计「告警回调拿不到报文体」的次数，用于限频告警（见 _extract_alarm_event）
_EMPTY_PAYLOAD_COUNT = 0


class IsupRuntime:
    """持有 CMS/AMS/SS 服务实例，负责启动与优雅停止。"""

    def __init__(self) -> None:
        self.cms: Any = None
        self.ams: Any = None
        self.ss: Any = None
        self.sms: Any = None
        self.started = False
        self.last_error: str | None = None
        # ★ 必须持有 C 回调函数指针的强引用：
        #   ctypes 回调对象一旦被 GC，C 层再回调就是野指针 → 进程崩溃
        self._keepalive: list[Any] = []

    # ------------------------------------------------------------------ 启动
    def start(self) -> bool:
        settings = get_settings()
        if not settings.enable_isup_sdk:
            logger.info("ISUP SDK 已被配置禁用（ISUP_ENABLE_ISUP_SDK=false）")
            self.last_error = "disabled by config"
            return False

        # 事件总线必须已绑定事件循环，否则回调事件会被丢弃
        from server.services.bus import bus as _bus

        if _bus._loop is None:
            logger.warning("事件总线尚未绑定事件循环，SDK 回调事件将无法送达")

        ok, reason = sdk_available()
        if not ok:
            logger.warning("ISUP SDK 不可用，服务将以「无 SDK 模式」运行：%s", reason)
            self.last_error = reason
            return False

        try:
            ensure_src_importable()
            self._load_conf_to_global()
            self._patch_callbacks()
            self._start_services()
        except Exception as exc:
            logger.exception("ISUP SDK 启动失败")
            self.last_error = str(exc)
            return False

        self.started = True
        logger.info("ISUP SDK 已启动（CMS/AMS/SS 监听中）")
        return True

    def _load_conf_to_global(self) -> None:
        """把配置写进现有代码依赖的 glo 全局字典。

        原实现由 ConfRead.getConfJson() 从 cwd 相对路径读取，
        服务化后 cwd 不对，所以这里用绝对路径版本替代。
        """
        from src.Common import glo

        conf = get_isup_conf()
        glo._init()
        for section in ("ss", "cms", "ams", "sms"):
            for key, value in conf.get(section, {}).items():
                glo.set_value(key, value)
        glo.set_value("ISUPKey", conf.get("ISUPKey", ""))
        glo.set_value("iUserID", -1)
        glo.set_value("stopPlayBackFlag", True)
        logger.info("ISUP 配置已加载: CMS=%s:%s", conf["cms"]["CmsServerIP"], conf["cms"]["CmsServerPort"])

    # ------------------------------------------------------------------ 回调桥接
    def _patch_callbacks(self) -> None:
        """★ 关键：包装现有回调模块，把 C 线程事件转成 asyncio 事件。

        通过**替换模块级回调函数引用**实现，不改动 src/ 下的文件内容。

        ⚠️ 两个必须注意的点：
          1. 回调必须是 fun_ctype(...) 包装的 C 函数指针实例，
             直接赋普通 Python 函数会报 "expected WinFunctionType instance, got function"。
          2. 现有代码用 `from ... import X` 把回调**早已绑定**成模块级名字，
             所以要同时替换「定义处」和「使用处」的引用。
        """
        import ctypes as _ctypes

        from src.SdkService.AlarmService import AlarmDemo
        from src.SdkService.AlarmService.HCISUPAlarm import (
            EHomeMsgCallBack as AlarmCBType,
        )
        from src.SdkService.CmsService import CmsDemo
        from src.SdkService.CmsService.HCISUPCMS import fun_ctype
        from src.SdkService.SsService import SSCallBack
        from src.SdkService.SsService.HCISUPSS import (
            EHomeSStorageCallBack as StorageCBType,
        )

        # ⚠️ 不要在这里 bind_loop：本方法由 run_in_executor 在**工作线程**里调用，
        #    该线程没有事件循环，get_event_loop() 会抛 RuntimeError。
        #    事件循环已在 server/main.py 的 lifespan 中绑定好。

        # ---- ① 告警回调 ----
        # ★ 回调日志限频：前 20 条全打印（便于现场看清报文形态），之后每 100 条一次。
        #   原因：这段跑在 SDK 的 C 回调线程里，print(flush=True) 是同步系统调用。
        #   设备断线风暴时回调可能几千次/分钟，逐条刷日志会拖慢该线程，
        #   进而影响 SDK 收包；同时白耗 docker json-file 的 IO。
        _cb_stat = {"n": 0}
        _CB_PRINT_HEAD = 20
        _CB_PRINT_EVERY = 100

        def _alarm_impl(iHandle, pAlarmMsg, pUser):
            _cb_stat["n"] += 1
            _n = _cb_stat["n"]
            _verbose = _n <= _CB_PRINT_HEAD or _n % _CB_PRINT_EVERY == 0

            if _verbose:
                print(
                    f"[ALARM-CB] 回调触发 #{_n} iHandle={iHandle} "
                    f"pMsg={'有' if pAlarmMsg else '空'}",
                    flush=True,
                )
            try:
                event = _extract_alarm_event(pAlarmMsg)
                if event is not None:
                    if _verbose:
                        print(
                            f"[ALARM-CB] 解析成功 device={event.get('device_id')!r} "
                            f"ch={event.get('channel')} type={event.get('alarm_type')} "
                            f"len={len(event.get('content_raw') or '')}",
                            flush=True,
                        )
                    bus.emit_from_thread(event)
                elif _verbose:
                    print("[ALARM-CB] 解析结果为空（已丢弃）", flush=True)
            except Exception:
                logger.exception("解析告警报文失败")
            return True  # 必须返回 True，否则 SDK 会认为回调失败

        alarm_callback = AlarmCBType(_alarm_impl)
        AlarmDemo.EHomeMsgCallBack = alarm_callback
        # 有些路径直接引用了 HCISUPAlarm.EHomeMsgCallBack，一并替换
        import src.SdkService.AlarmService.HCISUPAlarm as _alarm_mod

        _alarm_mod.EHomeMsgCallBack = alarm_callback
        self._keepalive.extend([_alarm_impl, alarm_callback])

        # ---- ② 存储回调（图片）----
        def _storage_impl(iHandle, pFileName, pFileBuf, dwFileLen, pFilePath, pUser):
            try:
                data = ctypes.string_at(pFileBuf, dwFileLen)
                name = _read_c_str(pFileName)
                puser_str = _device_from_user(pUser)
                logger.info(
                    "★ SS 回调收到图片: pFileName=%r (%s) len=%d pUser=%r",
                    name,
                    type(pFileName).__name__,
                    dwFileLen,
                    puser_str,
                )
                bus.emit_from_thread(
                    {
                        "kind": "storage_image",
                        "file_name": name,
                        "data": data,
                        "captured_at": datetime.now(),
                        # ★ device_id 目前拿不到 —— 见 docs 风险 R2。
                        #  P0 探针已注入 pUserData，若 SDK 透传则这里能拿到。
                        "device_id": puser_str,
                        "channel": None,
                    }
                )
            except Exception:
                logger.exception("处理存储回调失败")
            return True

        storage_callback = StorageCBType(_storage_impl)
        SSCallBack.pss_storage_callback = storage_callback
        self._keepalive.extend([_storage_impl, storage_callback])

        # ---- ③ 设备注册回调（维护在线状态）----
        original_register = CmsDemo.deviceRegisterCB

        def _register_impl(lUserID, dwDataType, pOutBuffer, dwOutLen, pInBuffer, dwInLen, pUser):
            result = None
            try:
                result = original_register(
                    lUserID, dwDataType, pOutBuffer, dwOutLen, pInBuffer, dwInLen, pUser
                )
            except Exception:
                logger.exception("原始注册回调执行失败")
            try:
                # ★ dwDataType：0=上线 1=离线（其余 3/4/5 是密钥/会话协商，不产生设备事件）
                if dwDataType in (0, 1):
                    if dwDataType == 0:
                        device_id = _device_id_from_reg(pOutBuffer)
                    else:
                        # ★ 离线报文的 pOutBuffer 不是 REG_INFO 结构！
                        #   用上线时登记的 userDeviceMap（deviceID ↔ lUserID）反查。
                        device_id = _device_id_from_usermap(lUserID)
                    logger.info(
                        "设备事件: deviceID=%s online=%s iUserID=%s",
                        device_id,
                        dwDataType == 0,
                        lUserID,
                    )
                    bus.emit_from_thread(
                        {
                            "kind": "device",
                            "device_id": device_id,
                            "user_id": lUserID,
                            "online": dwDataType == 0,
                            "data_type": dwDataType,
                        }
                    )
            except Exception:
                logger.exception("处理设备注册事件失败")
            return True if result is None else result

        register_callback = fun_ctype(
            _ctypes.c_bool,
            _ctypes.c_int16,
            _ctypes.c_uint32,
            _ctypes.POINTER(_ctypes.c_void_p),
            _ctypes.c_uint32,
            _ctypes.POINTER(_ctypes.c_void_p),
            _ctypes.c_uint32,
            _ctypes.POINTER(_ctypes.c_void_p),
        )(_register_impl)
        CmsDemo.deviceRegisterCB = register_callback
        self._keepalive.extend([_register_impl, register_callback])

        logger.info("SDK 回调已桥接到事件总线")

    def _start_services(self) -> None:
        from src.SdkService.AlarmService.AlarmDemo import amsClass
        from src.SdkService.CmsService.CmsDemo import cmsClass
        from src.SdkService.SsService.SsDemo import ssClass
        from src.SdkService.StreamService.StreamDemo import smsClass

        self.ams = amsClass()
        self.ams.startAmsListen()

        self.ss = ssClass()
        self.ss.startSsListen()

        self.cms = cmsClass()
        self.cms.startCmsListen()

        # ★ sms（取流/回放）需要一个 cmsDLL 已就绪的实例；
        #   它不主动开监听，只在收到回放请求时才 startPlayBackListen_FILE。
        #   回放服务通过 isup_runtime.sms 拿到它。
        self.sms = smsClass()

    # ------------------------------------------------------------------ 停止
    def stop(self) -> None:
        for svc in (self.sms, self.cms, self.ams, self.ss):
            if svc is None:
                continue
            try:
                if svc is self.cms:
                    svc.stopCmsListen()
                elif svc is self.ams:
                    svc.stopAmsListen()
                elif svc is self.ss:
                    svc.stopSsListen()
                else:
                    svc.stopSmsListen()
            except Exception:
                logger.exception("停止 ISUP 服务失败")
        self.started = False
        logger.info("ISUP SDK 已停止")


# --------------------------------------------------------------------------
# 报文解析辅助
# --------------------------------------------------------------------------
def _read_c_str(value: Any) -> str:
    """安全地把 c_char_p / bytes / 指针 读成字符串。

    ⚠️ 现有 SSCallBack 直接用 string_at(pFileName)，但 c_char_p 作为回调
    入参在 ctypes 里会被自动转成 bytes，再 string_at 行为不确定（docs §2.2②）。
    这里做健壮处理 —— 这也是 P0 要验证的点。
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip("\x00").strip()
    if isinstance(value, str):
        return value.strip("\x00").strip()
    try:
        return ctypes.string_at(value).decode("utf-8", errors="replace").strip("\x00").strip()
    except Exception:
        return ""


def _device_from_user(pUser: Any) -> str:
    """从 pUser 解出设备上下文。

    ★ 目前 SsDemo.startSsListen() 没有给 pUserData 赋值，所以这里恒为空。
      修复方式见 patch_ss_userdata()。
    """
    if not pUser:
        return ""
    try:
        return ctypes.cast(pUser, ctypes.c_char_p).value.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _device_id_from_reg(pOutBuffer: Any) -> str:
    try:
        from src.SdkService.CmsService.HCISUPCMS import LPNET_EHOME_DEV_REG_INFO_V12

        info = ctypes.cast(pOutBuffer, LPNET_EHOME_DEV_REG_INFO_V12).contents
        return str(info.struRegInfo.byDeviceID, encoding="utf-8").rstrip("\x00")
    except Exception:
        return ""


def _device_id_from_usermap(lUserID: int) -> str:
    """★ 离线事件反查 deviceID。

    离线报文（dwDataType=1）的 pOutBuffer 不携带设备注册信息，
    但上线（dwDataType=0）时 CmsDemo 已把 (deviceID ↔ lUserID) 登记
    在 glo.userDeviceMap —— 按句柄反查即可拿到准确 ID。

    ★ 映射方向：userDeviceMap 是 {lUserID: deviceID}（见 glo.register_device），
      直接 .get(lUserID)。
      ⚠️ 2026-XX 修复一个**存量 bug**：原实现把 items 解包成
      (device_id, uid) 再拿 uid 和 lUserID 比 —— 实际键值方向相反，
      永远比不中，离线事件的设备 ID 一直是空串（与 CmsDemo.py:101
      的 `.get(lUserID)` 正确写法对照确认）。

    ★ 用快照读取（2026-XX 并发加固）：本函数跑在 SDK 回调线程，
      主线程可能正在 register/unregister 修改同一个 dict ——
      先 dict() 拷贝再查，避免迭代期变更异常。
    """
    try:
        from src.Common import glo

        user_map = dict(glo.get_value("userDeviceMap", {}) or {})
        device_id = user_map.get(lUserID)
        if device_id:
            return str(device_id)
    except Exception:
        pass
    return ""


def _extract_alarm_event(pAlarmMsg: Any) -> dict | None:
    """★ 解析 NET_EHOME_ALARM_MSG。

    同时处理两种情况（docs §3.1）：
      情况 A：报文自带图片（byPicturesNumber > 0）→ inline_pictures
      情况 B：只有告警内容，图片稍后走 SS 回调
    """
    from src.SdkService.AlarmService.HCISUPAlarm import (
        LPNET_EHOME_ALARM_ISAPI_INFO,
        LPNET_EHOME_ALARM_MSG,
    )

    msg = ctypes.cast(pAlarmMsg, LPNET_EHOME_ALARM_MSG).contents
    alarm_type = int(msg.dwAlarmType)

    content_raw = None
    if msg.dwXmlBufLen and msg.pXmlBuf:
        raw = ctypes.string_at(msg.pXmlBuf, msg.dwXmlBufLen)
        content_raw = raw.decode("utf-8", errors="replace").rstrip("\x00")

    device_id = ""
    # ★ 不用 1 当默认值：0 表示「本回调没能确定通道」，
    #   由 correlator 用报文解析结果（更权威）来填。
    #   旧实现默认 1，会让 XML 报文的真实通道号被静默丢弃。
    channel = 0
    content_json = None
    inline_pictures: list[dict] = []

    if alarm_type == 13 and msg.dwAlarmInfoLen > 0 and msg.pAlarmInfo:
        isapi = ctypes.cast(msg.pAlarmInfo, LPNET_EHOME_ALARM_ISAPI_INFO).contents

        if isapi.dwAlarmDataLen and isapi.pAlarmData:
            data = ctypes.string_at(isapi.pAlarmData, isapi.dwAlarmDataLen)
            text = data.decode("utf-8", errors="replace").rstrip("\x00")
            # ★★ 2026-10-29 修复（现场实测：1 小时 488 条「无设备、无类型」告警）
            #
            #   原实现：
            #       content_json = _try_parse_json(text)
            #       if content_json:                     # ← 只有 JSON 才进来
            #           content_raw = text or content_raw
            #
            #   问题：ISAPI 报文有两种形态 —— JSON（AIOP 等）和 **XML**
            #   （VMD / IO / 大多数海康事件）。XML 时 _try_parse_json 返回 None，
            #   于是 text 从来没写进 content_raw：
            #       · dwXmlBuf 为空时（type=13 常见）→ content_raw 恒为 None
            #       · 下游 alarm_parser 没有任何内容可解析
            #       · 结果：device_id=""、eventType=""、channel=0
            #   界面上这类告警只能走兜底文案「ISAPI 事件上报」，
            #   看起来像「ISAPI 一直在报警」，其实是报文被丢掉了。
            #
            #   修法：JSON/XML 一律先保底写进 content_raw，再做 JSON 增强解析。
            #   （content_raw 优先用 ISAPI 报文，dwXmlBuf 作为后备）
            if text:
                content_raw = text or content_raw
            content_json = _try_parse_json(text)
            if content_json:
                device_id = str(
                    content_json.get("deviceID")
                    or content_json.get("DeviceID")
                    or content_json.get("ipAddress")
                    or ""
                )
                # 兼容多种键名；解析不到就保持 0（交给 correlator 兜底）
                for _k in ("channelID", "channel", "channelNo"):
                    _v = content_json.get(_k)
                    if _v not in (None, ""):
                        try:
                            channel = int(str(_v).strip())
                        except (TypeError, ValueError):
                            channel = 0
                        break

        # ---- 情况 A：报文自带的图片 ----
        count = int(getattr(isapi, "byPicturesNumber", 0) or 0)
        if count > 0 and isapi.pPicPackData:
            inline_pictures = _extract_inline_pictures(isapi.pPicPackData, count)

    # ★★ 2026-10-29 修复（现场：摄像头拔线后 1 小时堆了 488 条空告警）
    #
    #   设备断线/重连时，SDK 会反复触发告警回调，但**没有任何报文体**：
    #   dwXmlBufLen=0 且 pAlarmData 为空 → content_raw=None、device_id=""。
    #
    #   若放行，每一条空回调都会落一条「无设备、无类型」的库记录，
    #   界面走兜底文案，看着像在刷屏，实际是断线风暴。
    #   这类回调既无报文也无设备号，落库后对任何车间都不可见，
    #   纯属污染。直接丢弃，并限频告警（每 100 条一次）。
    if not content_raw and not device_id:
        global _EMPTY_PAYLOAD_COUNT
        _EMPTY_PAYLOAD_COUNT += 1
        if _EMPTY_PAYLOAD_COUNT == 1 or _EMPTY_PAYLOAD_COUNT % 100 == 0:
            logger.warning(
                "丢弃无报文告警回调（累计 %d 条，alarm_type=%s）："
                "既无报文体也无设备号，无法归属车间。"
                "常见于设备断线/重连风暴，属正常丢弃",
                _EMPTY_PAYLOAD_COUNT,
                alarm_type,
            )
        return None

    return {
        "kind": "alarm",
        "alarm_type": alarm_type,
        "device_id": device_id,
        "channel": channel,
        "alarm_time": datetime.now(),
        "content_raw": content_raw,
        "content_json": content_json,
        "inline_pictures": inline_pictures,
    }


def _extract_inline_pictures(pPicPackData: Any, count: int) -> list[dict]:
    """从 pPicPackData 解出 byPicturesNumber 个 NET_EHOME_ALARM_ISAPI_PICDATA。

    ⚠️ 该结构体在现有 HCISUPAlarm.py 里**尚未定义**，这里按 SDK 常规布局
      做保守解析，并在 P0 脚本里验证。解析失败不影响主流程。
    """
    try:
        from src.SdkService.CmsService.HCISUPCMS import C_BYTE, C_DWORD
        from ctypes import Structure, c_void_p

        class PICDATA(Structure):
            _fields_ = [
                ("pPicData", c_void_p),  # 图片数据
                ("dwPicSize", C_DWORD),  # 图片大小
                ("byRes", C_BYTE * 64),
            ]

        arr = ctypes.cast(pPicPackData, ctypes.POINTER(PICDATA))
        out: list[dict] = []
        for i in range(min(count, 32)):
            item = arr[i]
            if not item.pPicData or not item.dwPicSize:
                continue
            out.append(
                {
                    "name": f"inline_{i}.jpg",
                    "data": ctypes.string_at(item.pPicData, item.dwPicSize),
                }
            )
        return out
    except Exception:
        logger.exception("解析报文内嵌图片失败（不影响主流程）")
        return []


def _try_parse_json(text: str) -> dict | None:
    import json

    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {"raw": obj}
    except Exception:
        return None


runtime = IsupRuntime()
