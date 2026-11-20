# -*- coding: utf-8 -*-
"""用 HCNetSDK 布防收 ISAPI 报警（COMM_ISAPI_ALARM），替代 ISUP AMS。

官方路径（报警布防 Demo）：
  NET_DVR_Init → Login_V40(byLoginMode=1 ISAPI) → SetupAlarmChan_V41
  回调 lCommand=0x6009 → NET_DVR_ALARM_ISAPI_INFO（XML/JSON + 图）
"""

from __future__ import annotations

import ctypes
import logging
import os
import re
import threading
from ctypes import byref, cast, create_string_buffer, sizeof, string_at
from pathlib import Path

from server.adapters import hcnetsdk as sdk
from server.services.bus import bus
from server.services.timeutil import now_local, parse_any

logger = logging.getLogger(__name__)

DEFAULT_SDK_DIR = str(Path(__file__).resolve().parents[2] / "lib" / "hcnetsdk")


class HcnetAlarmListener:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._th: threading.Thread | None = None
        self._dll = None
        self._user_id = -1
        self._alarm_handle = -1
        self._cb = None  # 必须挂实例上，否则回调被 GC

    def start(self) -> None:
        if self._th and self._th.is_alive():
            return
        self._stop.clear()
        self._th = threading.Thread(target=self._run, name="hcnet-alarm", daemon=True)
        self._th.start()
        logger.info("HCNetSDK 布防线程已启动")

    def stop(self) -> None:
        self._stop.set()
        self._teardown()
        if self._th and self._th.is_alive():
            self._th.join(timeout=4)
        logger.info("HCNetSDK 布防已停止")

    def _run(self) -> None:
        from server.config import get_settings

        while not self._stop.is_set():
            settings = get_settings()
            host = (getattr(settings, "isapi_host", "") or "").strip()
            password = getattr(settings, "isapi_password", "") or ""
            if not host or not password:
                logger.warning("HCNetSDK 布防缺少 host/password")
                self._stop.wait(10)
                continue
            try:
                self._session(settings)
            except Exception as exc:
                # 配置错误（如 ISAPI 口配成 8000）会每 5s 重试；
                # 已知错误码只打一行，避免刷满 traceback。
                msg = str(exc)
                if "Login_V40" in msg and "err=9" in msg:
                    logger.error(
                        "HCNetSDK 布防会话失败：%s（ISAPI 登录请用 HTTP 口，"
                        "一般是 ISUP_ISAPI_PORT=80；8000 是私有协议口）",
                        msg,
                    )
                else:
                    logger.exception("HCNetSDK 布防会话失败")
                self._teardown()
                self._emit_device(settings, False)
            if not self._stop.is_set():
                self._stop.wait(5)

    def _session(self, settings) -> None:
        lib_dir = Path(
            getattr(settings, "hcnetsdk_dir", "") or DEFAULT_SDK_DIR
        ).expanduser()
        so = lib_dir / "libhcnetsdk.so"
        if not so.is_file():
            raise FileNotFoundError(f"找不到 {so}")

        os.environ.setdefault("LD_LIBRARY_PATH", "")
        if str(lib_dir) not in os.environ["LD_LIBRARY_PATH"].split(":"):
            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{os.environ['LD_LIBRARY_PATH']}"

        dll = ctypes.cdll.LoadLibrary(str(so))
        self._dll = dll
        self._set_sdk_path(dll, lib_dir)

        if not dll.NET_DVR_Init():
            raise RuntimeError(f"NET_DVR_Init 失败 err={dll.NET_DVR_GetLastError()}")

        gen = sdk.NET_DVR_LOCAL_GENERAL_CFG()
        gen.byAlarmJsonPictureSeparate = 1
        dll.NET_DVR_SetSDKLocalCfg(sdk.NET_DVR_LOCAL_CFG_TYPE_GENERAL, byref(gen))

        self._cb = sdk.MSGCallBack_V31(self._on_alarm)
        dll.NET_DVR_SetDVRMessageCallBack_V31(self._cb, None)

        # byLoginMode: 0=私有协议 1=ISAPI 2=自适应
        # ISAPI 登录必须走 HTTP 口（通常 80）；8000 是私有协议口，
        # 配错会 Login_V40 err=9（NETWORK_RECV_ERROR）。
        login_mode = int(getattr(settings, "hcnetsdk_login_mode", 1) or 1)
        port = _resolve_login_port(settings, login_mode)

        login = sdk.NET_DVR_USER_LOGIN_INFO()
        login.bUseAsynLogin = 0
        login.sDeviceAddress = host_bytes(settings.isapi_host)
        login.wPort = port
        login.sUserName = str(settings.isapi_username or "admin").encode("utf-8")
        login.sPassword = str(settings.isapi_password).encode("utf-8")
        login.byLoginMode = login_mode

        mode_name = {0: "Private", 1: "ISAPI", 2: "Auto"}.get(login_mode, str(login_mode))
        dev = sdk.NET_DVR_DEVICEINFO_V40()
        uid = dll.NET_DVR_Login_V40(byref(login), byref(dev))
        if uid < 0:
            err = dll.NET_DVR_GetLastError()
            hint = ""
            if err == 9 and login_mode == 1 and port == 8000:
                hint = "；ISAPI 模式不要用 8000，请改 ISUP_HCNETSDK_PORT=80 或 ISUP_ISAPI_PORT"
            raise RuntimeError(f"Login_V40 失败 err={err} mode={mode_name} port={port}{hint}")
        self._user_id = uid
        serial = bytes(dev.struDeviceV30.sSerialNumber).split(b"\x00", 1)[0].decode(
            "utf-8", "replace"
        )
        logger.info(
            "HCNetSDK 登录成功 user=%s serial=%s mode=%s port=%s",
            uid,
            serial,
            mode_name,
            port,
        )

        param = sdk.NET_DVR_SETUPALARM_PARAM()
        param.dwSize = sizeof(param)
        param.byAlarmInfoType = 1
        param.byDeployType = 1  # 实时布防
        handle = dll.NET_DVR_SetupAlarmChan_V41(uid, byref(param))
        if handle < 0:
            raise RuntimeError(
                f"SetupAlarmChan_V41 失败 err={dll.NET_DVR_GetLastError()}"
            )
        self._alarm_handle = handle
        logger.info("HCNetSDK 布防成功 handle=%s → %s", handle, settings.isapi_host)
        self._emit_device(settings, True)

        while not self._stop.is_set():
            self._stop.wait(2)

        self._teardown()

    def _set_sdk_path(self, dll, lib_dir: Path) -> None:
        com = sdk.NET_DVR_LOCAL_SDK_PATH()
        com.sPath = str(lib_dir).encode("utf-8")
        dll.NET_DVR_SetSDKInitCfg(sdk.NET_SDK_INIT_CFG_SDK_PATH, byref(com))
        crypto = lib_dir / "libcrypto.so.3"
        ssl = lib_dir / "libssl.so.3"
        if crypto.is_file():
            dll.NET_DVR_SetSDKInitCfg(
                sdk.NET_SDK_INIT_CFG_LIBEAY_PATH,
                create_string_buffer(str(crypto).encode("utf-8")),
            )
        if ssl.is_file():
            dll.NET_DVR_SetSDKInitCfg(
                sdk.NET_SDK_INIT_CFG_SSLEAY_PATH,
                create_string_buffer(str(ssl).encode("utf-8")),
            )

    def _teardown(self) -> None:
        dll = self._dll
        if dll is None:
            return
        try:
            if self._alarm_handle >= 0:
                dll.NET_DVR_CloseAlarmChan_V30(self._alarm_handle)
        except Exception:
            pass
        try:
            if self._user_id >= 0:
                dll.NET_DVR_Logout(self._user_id)
        except Exception:
            pass
        try:
            dll.NET_DVR_Cleanup()
        except Exception:
            pass
        self._alarm_handle = -1
        self._user_id = -1
        self._dll = None

    def _on_alarm(self, lCommand, pAlarmer, pAlarmInfo, dwBufLen, pUser) -> bool:
        try:
            if lCommand != sdk.COMM_ISAPI_ALARM or not pAlarmInfo:
                return True
            from server.config import get_settings

            settings = get_settings()
            info = cast(pAlarmInfo, sdk.LPNET_DVR_ALARM_ISAPI_INFO).contents
            text = ""
            if info.dwAlarmDataLen and info.pAlarmData:
                text = string_at(info.pAlarmData, info.dwAlarmDataLen).decode(
                    "utf-8", "replace"
                )
            if not text.strip():
                return True
            low = text.lower()
            event_type = (_xml_tag(text, "eventType") or _json_field(text, "eventType")).lower()
            if event_type in ("heartbeat", "videoloss", "upload") or "<heartbeat" in low:
                return True
            event_state = (
                _xml_tag(text, "eventState") or _json_field(text, "eventState")
            ).lower()
            if event_state in ("inactive", "end"):
                return True

            channel = (
                _int_field(text, ("channelID", "dynChannelID", "channelNo", "channel"))
                or 1
            )
            raw_dev = (
                _xml_tag(text, "deviceID")
                or _json_field(text, "deviceID")
                or ""
            ).strip()
            # 设备常上报未替换模板 "@deviceId@"，不能当真设备名
            if not raw_dev or (raw_dev.startswith("@") and raw_dev.endswith("@")):
                raw_dev = getattr(settings, "isapi_device_id", "") or "box001"
            device_id = raw_dev
            dt_raw = _xml_tag(text, "dateTime") or _json_field(text, "dateTime")
            alarm_time = parse_any(dt_raw) or now_local()
            pics = _copy_pics(info)
            # 尽量带上解析后的 JSON，便于聚合器读 url / ipAddress
            content_json = None
            if text.lstrip().startswith("{"):
                try:
                    import json as _json

                    content_json = _json.loads(text)
                except Exception:
                    content_json = None
            bus.emit_from_thread(
                {
                    "kind": "alarm",
                    "alarm_type": 13,
                    "device_id": device_id,
                    "channel": channel,
                    "alarm_time": alarm_time,
                    "alarm_time_explicit": True,
                    "content_raw": text,
                    "content_json": content_json,
                    "inline_pictures": pics,
                }
            )
            logger.info(
                "HCNetSDK ISAPI 报警 %s ch=%s type=%s pics=%d url=%s",
                device_id,
                channel,
                event_type,
                len(pics),
                "yes" if isinstance(content_json, dict) and content_json.get("url") else "no",
            )
        except Exception:
            logger.exception("HCNetSDK 报警回调异常")
        return True

    def _emit_device(self, settings, online: bool) -> None:
        device_id = getattr(settings, "isapi_device_id", "") or "box001"
        bus.emit_from_thread(
            {
                "kind": "device",
                "device_id": device_id,
                "online": online,
            }
        )


def host_bytes(host: str) -> bytes:
    return str(host).encode("utf-8")[:128]


def _resolve_login_port(settings, login_mode: int) -> int:
    """按登录模式选端口，避免 ISAPI@8000 这类必败组合。

    - mode=1 (ISAPI)：优先 isapi_port，其次 hcnetsdk_port；若仍是 8000 则强制改 80
    - mode=0 (Private)：优先 hcnetsdk_port，默认 8000
    - mode=2 (Auto)：优先 hcnetsdk_port，否则 isapi_port
    """
    hc_port = int(getattr(settings, "hcnetsdk_port", 0) or 0)
    isapi_port = int(getattr(settings, "isapi_port", 0) or 0)

    if login_mode == 1:
        port = isapi_port or hc_port or 80
        if port == 8000:
            logger.warning(
                "HCNetSDK ISAPI 登录端口被配成 8000（私有协议口），已改用 80；"
                "请把 ISUP_HCNETSDK_PORT 改成 80，或设 ISUP_ISAPI_PORT"
            )
            return 80
        return port
    if login_mode == 0:
        return hc_port or 8000
    return hc_port or isapi_port or 8000


def _copy_pics(info) -> list[dict]:
    n = int(info.byPicturesNumber or 0)
    if n <= 0 or not info.pPicPackData:
        return []
    arr_t = sdk.NET_DVR_ALARM_ISAPI_PICDATA * n
    arr = cast(info.pPicPackData, ctypes.POINTER(arr_t)).contents
    out = []
    for i in range(n):
        item = arr[i]
        if not item.dwPicLen or not item.pPicData:
            continue
        name = (item.szFilename or b"").decode("utf-8", "replace").strip("\x00") or f"isapi_{i}.jpg"
        out.append({"name": name, "data": string_at(item.pPicData, item.dwPicLen)})
    return out


def _xml_tag(text: str, tag: str) -> str:
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", text, re.I)
    return (m.group(1) if m else "").strip()


def _json_field(text: str, key: str) -> str:
    if not text.lstrip().startswith("{"):
        return ""
    m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text)
    return (m.group(1) if m else "").strip()


def _int_field(text: str, keys: tuple[str, ...]) -> int:
    for k in keys:
        v = _xml_tag(text, k) or _json_field(text, k)
        if v.isdigit():
            return int(v)
    return 0


hcnet_alarm_listener = HcnetAlarmListener()
