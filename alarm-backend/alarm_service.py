# -*- coding: utf-8 -*-
import os
import threading
import time
import traceback
from datetime import datetime

from event_parser import is_ppe_related, make_picture_name, parse_isapi_payload
from alarm_helpers import notify_alarm
from HCNetSDK import *


SDK_ERROR_MESSAGES = {
    1: "用户名或密码错误",
    7: "连接服务器失败（IP/端口/网络不通）",
    153: "用户已被锁定（多次密码错误，请等待或到 Web 解锁）",
}


class HikAlarmService:
    COMMAND_LABELS = {
        ALARM_LCOMMAND_ENUM.COMM_ALARM_V30.value: "COMM_ALARM_V30",
        ALARM_LCOMMAND_ENUM.COMM_ISAPI_ALARM.value: "COMM_ISAPI_ALARM",
        ALARM_LCOMMAND_ENUM.COMM_UPLOAD_FACESNAP_RESULT.value: "COMM_UPLOAD_FACESNAP_RESULT",
        ALARM_LCOMMAND_ENUM.COMM_SNAP_MATCH_ALARM.value: "COMM_SNAP_MATCH_ALARM",
    }

    def __init__(self, config, storage, notifier=None):
        self.config = config
        self.storage = storage
        self.notifier = notifier
        self.hik_sdk = None
        self.user_id = -1
        self.alarm_handle = -1
        self.listen_handle = -1
        self.running = False
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._status = {
            "state": "stopped",
            "last_error": None,
            "last_connected_at": None,
            "last_alarm_at": None,
            "reconnect_count": 0,
            "alarm_mode": config.get("alarm_mode", "deploy"),
        }
        self.msg_callback_func = MSGCallBack_V31(self._on_alarm_callback)

    @property
    def status(self):
        with self._lock:
            return dict(self._status)

    def _set_status(self, **kwargs):
        with self._lock:
            self._status.update(kwargs)

    def start(self):
        reconnect_cfg = self.config.get("reconnect", {})
        interval = int(reconnect_cfg.get("interval_seconds", 10))
        max_retries = reconnect_cfg.get("max_retries")

        attempt = 0
        self.running = True
        while self.running:
            try:
                self._set_status(state="connecting", last_error=None)
                self._connect_once()
                self._set_status(
                    state="connected",
                    last_connected_at=datetime.now().isoformat(timespec="seconds"),
                )
                self._ready.set()
                print("[alarm-service] 告警服务已启动，等待 NVR 推送事件...")
                while self.running:
                    time.sleep(1)
            except Exception as exc:
                attempt += 1
                err = f"{exc}"
                self._set_status(state="error", last_error=err, reconnect_count=attempt)
                print(f"[alarm-service] 连接失败: {err}")
                if max_retries is not None and attempt >= int(max_retries):
                    self._set_status(state="stopped", last_error=err)
                    print(
                        f"[alarm-service] 已达最大重试次数 ({max_retries})，停止 SDK 服务"
                    )
                    break
                print(f"[alarm-service] {interval}s 后重试...")
                self._cleanup_handles()
                time.sleep(interval)

    def wait_until_ready(self, timeout=30):
        return self._ready.wait(timeout=timeout)

    def stop(self):
        self.running = False
        self._cleanup_handles()
        self._set_status(state="stopped")

    def _cleanup_handles(self):
        if self.hik_sdk:
            if self.listen_handle > -1:
                self.hik_sdk.NET_DVR_StopListen_V30(self.listen_handle)
            if self.alarm_handle > -1:
                self.hik_sdk.NET_DVR_CloseAlarmChan_V30(self.alarm_handle)
            if self.user_id > -1:
                self.hik_sdk.NET_DVR_Logout(self.user_id)
            self.hik_sdk.NET_DVR_Cleanup()
        self.listen_handle = -1
        self.alarm_handle = -1
        self.user_id = -1
        self.hik_sdk = None

    def _connect_once(self):
        self.hik_sdk = self._load_sdk()
        self._set_sdk_init_cfg()
        if not self.hik_sdk.NET_DVR_Init():
            raise RuntimeError("NET_DVR_Init 失败")

        self._general_setting()
        nvr = self.config["nvr"]
        self._login(
            ip=nvr["ip"].encode("utf-8"),
            username=nvr["username"].encode("utf-8"),
            pwd=nvr["password"].encode("utf-8"),
            port=int(nvr.get("port", 8000)),
            login_mode=int(nvr.get("login_mode", 2)),
        )

        mode = self.config.get("alarm_mode", "deploy")
        if mode == "listen":
            listen_cfg = self.config.get("listen", {})
            self._start_listen(
                listen_cfg.get("host", "0.0.0.0").encode("utf-8"),
                int(listen_cfg.get("port", 7200)),
            )
            alarm_host = self.config.get("alarm_host")
            if alarm_host:
                self._set_nvr_alarm_host(
                    alarm_host.get("ip", "").encode("utf-8"),
                    int(alarm_host.get("port", listen_cfg.get("port", 7200))),
                )
        else:
            self._setup_alarm()

    def _load_sdk(self):
        print("netsdkdllpath:", netsdkdllpath)
        return load_library(netsdkdllpath)

    def _pick_ssl_dll_names(self, lib_path):
        lib_dir = lib_path.decode("gbk") if isinstance(lib_path, bytes) else lib_path
        candidates = [
            ("libcrypto-1_1-x64.dll", "libssl-1_1-x64.dll"),
            ("libcrypto-3-x64.dll", "libssl-3-x64.dll"),
        ]
        for crypto_name, ssl_name in candidates:
            if os.path.isfile(os.path.join(lib_dir, crypto_name)) and os.path.isfile(
                os.path.join(lib_dir, ssl_name)
            ):
                return crypto_name.encode("ascii"), ssl_name.encode("ascii")
        raise FileNotFoundError(
            "lib 目录缺少 OpenSSL DLL，请先运行: python setup_libs.py"
        )

    def _set_sdk_init_cfg(self):
        if sys_platform == "windows":
            base_path = os.path.dirname(__file__).encode("gbk")
            lib_path = base_path + b"\\lib"
            crypto_dll, ssl_dll = self._pick_ssl_dll_names(lib_path)
            sdk_com_path = NET_DVR_LOCAL_SDK_PATH()
            sdk_com_path.sPath = lib_path
            self.hik_sdk.NET_DVR_SetSDKInitCfg(
                NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_SDK_PATH.value,
                byref(sdk_com_path),
            )
            self.hik_sdk.NET_DVR_SetSDKInitCfg(
                NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_LIBEAY_PATH.value,
                create_string_buffer(lib_path + b"\\" + crypto_dll),
            )
            self.hik_sdk.NET_DVR_SetSDKInitCfg(
                NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_SSLEAY_PATH.value,
                create_string_buffer(lib_path + b"\\" + ssl_dll),
            )
        else:
            base_path = os.path.dirname(__file__).encode("utf-8")
            lib_path = base_path + b"/lib"
            sdk_com_path = NET_DVR_LOCAL_SDK_PATH()
            sdk_com_path.sPath = lib_path
            self.hik_sdk.NET_DVR_SetSDKInitCfg(
                NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_SDK_PATH.value,
                byref(sdk_com_path),
            )
            self.hik_sdk.NET_DVR_SetSDKInitCfg(
                NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_LIBEAY_PATH.value,
                create_string_buffer(lib_path + b"/libcrypto.so.1.1"),
            )
            self.hik_sdk.NET_DVR_SetSDKInitCfg(
                NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_SSLEAY_PATH.value,
                create_string_buffer(lib_path + b"/libssl.so.1.1"),
            )

    def _general_setting(self):
        log_dir = os.path.join(os.path.dirname(__file__), "SdkLog_Python")
        os.makedirs(log_dir, exist_ok=True)
        self.hik_sdk.NET_DVR_SetLogToFile(3, log_dir.encode("utf-8"), False)

        sdk_cfg = NET_DVR_LOCAL_GENERAL_CFG()
        sdk_cfg.byAlarmJsonPictureSeparate = 1
        self.hik_sdk.NET_DVR_SetSDKLocalCfg(
            NET_SDK_LOCAL_CFG_TYPE.NET_DVR_LOCAL_CFG_TYPE_GENERAL.value,
            byref(sdk_cfg),
        )
        self.hik_sdk.NET_DVR_SetDVRMessageCallBack_V31(self.msg_callback_func, None)

    def _login(self, ip, username, pwd, port, login_mode=2):
        login_info = NET_DVR_USER_LOGIN_INFO()
        login_info.bUseAsynLogin = 0
        login_info.sDeviceAddress = ip
        login_info.wPort = port
        login_info.sUserName = username
        login_info.sPassword = pwd
        login_info.byLoginMode = login_mode

        device_info = NET_DVR_DEVICEINFO_V40()
        self.user_id = self.hik_sdk.NET_DVR_Login_V40(byref(login_info), byref(device_info))
        if self.user_id < 0:
            err_code = self.hik_sdk.NET_DVR_GetLastError()
            err_hint = SDK_ERROR_MESSAGES.get(err_code, "请检查 IP、端口、账号密码")
            raise RuntimeError(
                f"NVR 登录失败, error code: {err_code} ({err_hint})"
            )

        serial = str(device_info.struDeviceV30.sSerialNumber, encoding="utf8").rstrip("\x00")
        print(f"[alarm-service] 登录成功, 设备序列号: {serial}")

    def _setup_alarm(self):
        alarm_param = NET_DVR_SETUPALARM_PARAM()
        alarm_param.dwSize = sizeof(alarm_param)
        alarm_param.byAlarmInfoType = 1
        alarm_param.byDeployType = 1
        self.alarm_handle = self.hik_sdk.NET_DVR_SetupAlarmChan_V41(
            self.user_id, byref(alarm_param)
        )
        if self.alarm_handle < 0:
            raise RuntimeError(
                "NET_DVR_SetupAlarmChan_V41 失败, error code: %d"
                % self.hik_sdk.NET_DVR_GetLastError()
            )
        print("[alarm-service] 报警布防成功")

    def _start_listen(self, listen_ip, listen_port):
        self.listen_handle = self.hik_sdk.NET_DVR_StartListen_V30(
            listen_ip, listen_port, self.msg_callback_func, None
        )
        if self.listen_handle < 0:
            raise RuntimeError(
                "NET_DVR_StartListen_V30 失败, error code: %d"
                % self.hik_sdk.NET_DVR_GetLastError()
            )
        print(f"[alarm-service] 报警监听已启动: {listen_ip.decode()}:{listen_port}")

    def _set_nvr_alarm_host(self, host_ip, host_port):
        out_buffer = NET_DVR_NETCFG_V50()
        out_buffer.dwSize = sizeof(out_buffer)
        returned = C_LPDWORD(c_uint(1))
        if not self.hik_sdk.NET_DVR_GetDVRConfig(
            self.user_id,
            NET_DVR_GET_NETCFG_V50,
            None,
            byref(out_buffer),
            out_buffer.dwSize,
            returned,
        ):
            raise RuntimeError(
                "读取 NVR 网络配置失败, error code: %d"
                % self.hik_sdk.NET_DVR_GetLastError()
            )
        out_buffer.struAlarmHostIpAddr.sIpV4 = host_ip
        out_buffer.wAlarmHostIpPort = host_port
        if not self.hik_sdk.NET_DVR_SetDVRConfig(
            self.user_id,
            NET_DVR_SET_NETCFG_V50,
            None,
            byref(out_buffer),
            out_buffer.dwSize,
        ):
            raise RuntimeError(
                "设置 NVR 报警主机失败, error code: %d"
                % self.hik_sdk.NET_DVR_GetLastError()
            )
        print(f"[alarm-service] 已设置 NVR 报警主机: {host_ip.decode()}:{host_port}")

    def _on_alarm_callback(self, l_command, p_alarmer, p_alarm_info, dw_buf_len, p_user):
        try:
            alarmer = p_alarmer.contents
            device_ip = str(alarmer.sDeviceIP, encoding="utf8").rstrip("\x00")
            device_serial = str(alarmer.sSerialNumber, encoding="utf8").rstrip("\x00")
            command_label = self.COMMAND_LABELS.get(l_command, hex(l_command))

            if l_command == ALARM_LCOMMAND_ENUM.COMM_ISAPI_ALARM.value:
                self._handle_isapi_alarm(device_ip, device_serial, command_label, p_alarm_info)
            elif l_command == ALARM_LCOMMAND_ENUM.COMM_ALARM_V30.value:
                self._handle_alarm_v30(device_ip, device_serial, command_label, p_alarm_info)
            else:
                alarm_id = self.storage.save_alarm(
                    device_ip=device_ip,
                    device_serial=device_serial,
                    command_type=command_label,
                    event_type="unsupported_event",
                    channel_no=None,
                    event_time=datetime.now().isoformat(timespec="seconds"),
                    raw_payload=f"收到未专门解析的事件: {command_label}",
                    picture_paths=[],
                    is_ppe_related=False,
                )
                notify_alarm(self.notifier, self.storage, alarm_id)
                print(f"[alarm-service] 收到事件: {command_label} from {device_ip}")

            self._set_status(last_alarm_at=datetime.now().isoformat(timespec="seconds"))
        except Exception as exc:
            print(f"[alarm-service] 回调处理异常: {exc}")
            traceback.print_exc()
        return True

    def _handle_isapi_alarm(self, device_ip, device_serial, command_label, p_alarm_info):
        alarm_struct = cast(p_alarm_info, LPNET_DVR_ALARM_ISAPI_INFO).contents
        parsed = parse_isapi_payload(b"")
        picture_paths = []

        data_len = alarm_struct.dwAlarmDataLen
        if data_len:
            raw_bytes = string_at(alarm_struct.pAlarmData, data_len)
            parsed = parse_isapi_payload(raw_bytes)

        pic_num = alarm_struct.byPicturesNumber
        if pic_num > 0:
            struct_type = NET_DVR_ALARM_ISAPI_PICDATA * pic_num
            pic_struct = cast(alarm_struct.pPicPackData, POINTER(struct_type)).contents
            for index in range(pic_num):
                pic_size = pic_struct[index].dwPicLen
                if pic_size:
                    pic_bytes = string_at(pic_struct[index].pPicData, pic_size)
                    pic_name = make_picture_name("isapi", index)
                    pic_path = os.path.join(self.storage.picture_dir, pic_name)
                    with open(pic_path, "wb") as fp:
                        fp.write(pic_bytes)
                    picture_paths.append(pic_path)

        keywords = self.config.get("event_filter_keywords", [])
        ppe_flag = is_ppe_related(
            parsed["event_type"],
            parsed["raw_text"],
            keywords,
            parsed=parsed,
        )
        alarm_id = self.storage.save_alarm(
            device_ip=device_ip,
            device_serial=device_serial,
            command_type=command_label,
            event_type=parsed["event_type"],
            channel_no=parsed["channel_no"],
            event_time=parsed["event_time"],
            raw_payload=parsed["raw_text"],
            picture_paths=picture_paths,
            is_ppe_related=ppe_flag,
        )
        notify_alarm(self.notifier, self.storage, alarm_id)
        print(
            f"[alarm-service] ISAPI告警入库 id={alarm_id}, "
            f"type={parsed['event_type']}, ppe={ppe_flag}, ip={device_ip}"
        )

    def _handle_alarm_v30(self, device_ip, device_serial, command_label, p_alarm_info):
        alarm_struct = cast(p_alarm_info, LPNET_DVR_ALARMINFO_V30).contents
        channel_no = alarm_struct.byChannel[0] if alarm_struct.byChannel else None
        event_type = f"motion_or_io_{hex(alarm_struct.dwAlarmType)}"
        alarm_id = self.storage.save_alarm(
            device_ip=device_ip,
            device_serial=device_serial,
            command_type=command_label,
            event_type=event_type,
            channel_no=channel_no,
            event_time=datetime.now().isoformat(timespec="seconds"),
            raw_payload=(
                f"dwAlarmType={hex(alarm_struct.dwAlarmType)}, channel={channel_no}"
            ),
            picture_paths=[],
            is_ppe_related=False,
        )
        notify_alarm(self.notifier, self.storage, alarm_id)
        print(f"[alarm-service] 基础告警入库 id={alarm_id}, type={event_type}")
