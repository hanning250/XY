# -*- coding: utf-8 -*-
"""海康 ISUP / EHome SDK（HCISUPSDKV2.5.1.35 Win64）的 ctypes 绑定。

与老的设备网络 SDK（HCNetSDK）最大的区别：
    老 SDK：服务器主动登录设备（NET_DVR_Login_V40），服务器是客户端。
    ISUP：  设备主动连服务器。服务器要
              1) NET_ECMS_StartListen   监听“设备注册端口”，设备上线
              2) NET_EALARM_StartListen 监听“报警端口”，收报警与图片

所以服务器不需要设备账号密码，只要设备侧把“平台地址/端口/设备ID/密钥”配对。

⚠ 头文件原文警告（必须遵守）：
    “严禁在报警回调函数中调用 HCISUPSDK 外部接口，否则可导致程序崩溃或堵死。”
    “回调中应避免耗时操作……耗时时间不宜超过 10ms。”
    因此回调里只能做「拷贝字节 + 入队」，DB / 写文件 / 网络必须在别的线程做。
"""

import os
import platform
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    byref,
    c_bool,
    c_byte,
    c_char,
    c_char_p,
    c_int,
    c_long,
    c_longlong,
    c_ulong,
    c_ushort,
    c_void_p,
    cdll,
    sizeof,
    string_at,
    windll,
)

# ---------------------------------------------------------------------------
# 平台 / 位数检查
# ---------------------------------------------------------------------------
sys_platform = platform.system().lower().strip()
python_bit_num = "".join(ch for ch in platform.architecture()[0] if ch.isdigit())
system_type = sys_platform + python_bit_num

if sys_platform == "windows":
    load_library = windll.LoadLibrary
    fun_ctype = CFUNCTYPE
elif sys_platform == "linux":
    load_library = cdll.LoadLibrary
    fun_ctype = CFUNCTYPE
else:
    raise RuntimeError(f"不支持的平台: {sys_platform}")

if python_bit_num != "64" and sys_platform == "windows":
    raise RuntimeError(
        "ISUP SDK 只能用 64 位 Python（SDK 提供的是 Win64 库）。"
        f"当前解释器是 {platform.architecture()[0]}。"
    )

# 本文件在 core/ 下，项目根目录是上一层
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(BASE_DIR, "lib_isup")

_DLL_NAMES = {
    "windows": {
        "alarm": "HCISUPAlarm.dll",
        "cms": "HCISUPCMS.dll",
    },
    "linux": {
        "alarm": "libHCISUPAlarm.so",
        "cms": "libHCISUPCMS.so",
    },
}


def _lib_path(key):
    return os.path.join(LIB_DIR, _DLL_NAMES[sys_platform][key])


# ---------------------------------------------------------------------------
# 基础类型别名（对齐 HCISUPPublic.h 里的 DWORD/BYTE/WORD/LONG）
# ---------------------------------------------------------------------------
C_BYTE = c_byte
C_WORD = c_ushort
C_DWORD = c_uint if sys_platform == "linux" else c_ulong
C_LONG = c_longlong if (sys_platform == "windows" and python_bit_num == "64") else c_long
C_BOOL = c_bool

# 长度宏（HCISUPPublic.h）
MAX_DEVICE_ID_LEN = 256
NET_EHOME_SERIAL_LEN = 12
MAX_MASTER_KEY_LEN = 16
MAX_FIRMWARE_IDENT_CODE_LEN = 128
MAX_DEVNAME_LEN_EX = 64
MAX_FULL_SERIAL_NUM_LEN = 64
MAX_FILE_PATH_LEN = 256

# EHOME_* 报警类型（HCISUPAlarm.h）
EHOME_ALARM_UNKNOWN = 0  # 未知报警类型
EHOME_ALARM = 1  # Ehome基本报警
EHOME_ALARM_HEATMAP_REPORT = 2  # 热度图报告
EHOME_ALARM_FACESNAP_REPORT = 3  # 人脸抓拍报告
EHOME_ALARM_GPS = 4  # GPS信息上传
EHOME_ALARM_CID_REPORT = 5  # 报警主机CID告警上传
EHOME_ALARM_NOTICE_PICURL = 6  # 图片URL上报
EHOME_ALARM_NOTIFY_FAIL = 7  # 异步失败通知
EHOME_ALARM_SELFDEFINE = 9  # 自定义报警上传
EHOME_ALARM_DEVICE_NETSWITCH_REPORT = 10  # 设备网络切换上传
EHOME_ALARM_ACS = 11  # 门禁事件上报
EHOME_ALARM_WIRELESS_INFO = 12  # 无线网络信息上传
EHOME_ISAPI_ALARM = 13  # ISAPI报警上传 ← 智能分析/防护服告警走这个
EHOME_INFO_RELEASE_PRIVATE = 14  # 信息发布产品私有协议（不再维护）
EHOME_ALARM_MPDCDATA = 15  # 车载设备客流数据
EHOME_ALARM_QRCODE = 20  # 二维码报警上传
EHOME_ALARM_FACETEMP = 21  # 人脸测温报警上传

ALARM_TYPE_LABELS = {
    EHOME_ALARM_UNKNOWN: "EHOME_ALARM_UNKNOWN",
    EHOME_ALARM: "EHOME_ALARM",
    EHOME_ALARM_HEATMAP_REPORT: "EHOME_ALARM_HEATMAP_REPORT",
    EHOME_ALARM_FACESNAP_REPORT: "EHOME_ALARM_FACESNAP_REPORT",
    EHOME_ALARM_GPS: "EHOME_ALARM_GPS",
    EHOME_ALARM_CID_REPORT: "EHOME_ALARM_CID_REPORT",
    EHOME_ALARM_NOTICE_PICURL: "EHOME_ALARM_NOTICE_PICURL",
    EHOME_ALARM_NOTIFY_FAIL: "EHOME_ALARM_NOTIFY_FAIL",
    EHOME_ALARM_SELFDEFINE: "EHOME_ALARM_SELFDEFINE",
    EHOME_ALARM_DEVICE_NETSWITCH_REPORT: "EHOME_ALARM_DEVICE_NETSWITCH_REPORT",
    EHOME_ALARM_ACS: "EHOME_ALARM_ACS",
    EHOME_ALARM_WIRELESS_INFO: "EHOME_ALARM_WIRELESS_INFO",
    EHOME_ISAPI_ALARM: "EHOME_ISAPI_ALARM",
    EHOME_INFO_RELEASE_PRIVATE: "EHOME_INFO_RELEASE_PRIVATE",
    EHOME_ALARM_MPDCDATA: "EHOME_ALARM_MPDCDATA",
    EHOME_ALARM_QRCODE: "EHOME_ALARM_QRCODE",
    EHOME_ALARM_FACETEMP: "EHOME_ALARM_FACETEMP",
}

# 设备注册回调的数据类型（NET_EHOME_REGISTER_TYPE）
ENUM_UNKNOWN = -1
ENUM_DEV_ON = 0  # 设备上线
ENUM_DEV_OFF = 1  # 设备下线
ENUM_DEV_ADDRESS_CHANGED = 2  # 设备地址变化
ENUM_DEV_AUTH = 3  # Ehome5.0设备认证回调
ENUM_DEV_SESSIONKEY = 4  # Ehome5.0设备Sessionkey回调
ENUM_DEV_DAS_REQ = 5  # Ehome5.0设备重定向请求回调
ENUM_DEV_SESSIONKEY_REQ = 6  # EHome5.0设备sessionkey请求回调
ENUM_DEV_DAS_REREGISTER = 7  # 设备重注册回调
ENUM_DEV_DAS_PINGREO = 8  # 设备注册心跳
ENUM_DEV_DAS_EHOMEKEY_ERROR = 9  # 校验密码失败
ENUM_DEV_SESSIONKEY_ERROR = 10  # Sessionkey交互异常
ENUM_DEV_SLEEP = 11  # 设备进入休眠

REGISTER_TYPE_LABELS = {
    ENUM_DEV_ON: "设备上线",
    ENUM_DEV_OFF: "设备下线",
    ENUM_DEV_ADDRESS_CHANGED: "设备地址变化",
    ENUM_DEV_AUTH: "设备认证",
    ENUM_DEV_SESSIONKEY: "SessionKey回调",
    ENUM_DEV_DAS_REQ: "重定向请求",
    ENUM_DEV_SESSIONKEY_REQ: "SessionKey请求",
    ENUM_DEV_DAS_REREGISTER: "设备重注册",
    ENUM_DEV_DAS_PINGREO: "注册心跳",
    ENUM_DEV_DAS_EHOMEKEY_ERROR: "校验密码失败",
    ENUM_DEV_SESSIONKEY_ERROR: "SessionKey交互异常",
    ENUM_DEV_SLEEP: "设备休眠",
}

# 本地配置类型（NET_EHOME_LOCAL_CFG_TYPE）
UNDEFINE = -1
ACTIVE_ACCESS_SECURITY = 0  # 设备主动接入的安全性
AMS_ADDRESS = 1  # 报警服务器本地回环地址
SEND_PARAM = 2  # 发送参数配置
SET_REREGISTER_MODE = 3  # 设备重复注册模式
LOCAL_CFG_TYPE_GENERAL = 4  # 通用参数配置
COM_PATH = 5  # COM路径
SESSIONKEY_REQ_MOD = 6  # sessionkey请求是否回调
DEV_DAS_PINGREO_CALLBACK = 7  # 设备心跳注册回调
REGISTER_LISTEN_MODE = 8  # 注册监听模式
STREAM_PLAYBACK_PARAM = 9  # 回放本地参数
RAPID_WAKEUP_MOD = 10  # 快速唤醒

# CMS / EALARM 初始化配置类型
NET_EHOME_CMS_INIT_CFG_LIBEAY_PATH = 0
NET_EHOME_CMS_INIT_CFG_SSLEAY_PATH = 1
NET_EHOME_EALARM_INIT_CFG_LIBEAY_PATH = 0
NET_EHOME_EALARM_INIT_CFG_SSLEAY_PATH = 1

# 注册监听模式
REGISTER_LISTEN_MODE_ALL = 0  # 监听 TCP 和 UDP
REGISTER_LISTEN_MODE_UDP = 1  # 只监听 UDP
REGISTER_LISTEN_MODE_TCP = 2  # 只监听 TCP

# 报警监听协议类型（NET_EHOME_ALARM_LISTEN_PARAM.byProtocolType）
PROTOCOL_TCP = 0
PROTOCOL_UDP = 1
PROTOCOL_MQTT = 2


# ---------------------------------------------------------------------------
# 结构体
# ---------------------------------------------------------------------------
class NET_EHOME_IPADDRESS(Structure):
    _fields_ = [
        ("szIP", c_char * 128),
        ("wPort", C_WORD),
        ("byRes", C_BYTE * 2),
    ]


class NET_EHOME_LOCAL_ACCESS_SECURITY(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        # 0-兼容模式(允许任意版本接入) 1-普通模式(仅4.0以下) 2-安全模式(仅4.0以上)
        ("byAccessSecurity", C_BYTE),
        ("byRes", C_BYTE * 127),
    ]


class NET_EHOME_REGISTER_LISTEN_MODE(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("dwRegisterListenMode", C_DWORD),  # 0-TCP+UDP 1-UDP 2-TCP
        ("byRes", C_BYTE * 128),
    ]


class NET_EHOME_SET_REREGISTER_MODE(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("dwReRegisterMode", C_DWORD),
    ]


class NET_EHOME_DEV_REG_INFO(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("dwNetUnitType", C_DWORD),
        ("byDeviceID", C_BYTE * MAX_DEVICE_ID_LEN),  # 设备ID
        ("byFirmwareVersion", C_BYTE * 24),
        ("struDevAdd", NET_EHOME_IPADDRESS),  # 设备注册上来的本地地址
        ("dwDevType", C_DWORD),
        ("dwManufacture", C_DWORD),
        ("byPassWord", C_BYTE * 32),  # 设备登录CMS的密码
        ("sDeviceSerial", C_BYTE * NET_EHOME_SERIAL_LEN),
        ("byReliableTransmission", C_BYTE),
        ("byWebSocketTransmission", C_BYTE),
        ("bySupportRedirect", C_BYTE),
        ("byDevProtocolVersion", C_BYTE * 6),
        ("bySessionKey", C_BYTE * MAX_MASTER_KEY_LEN),
        ("byMarketType", C_BYTE),
        ("byRes1", C_BYTE),
        ("bySupport", C_BYTE),
        ("byWakeupMode", C_BYTE),
        ("byRes", C_BYTE * 23),
    ]


class NET_EHOME_DEV_REG_INFO_V12(Structure):
    _fields_ = [
        ("struRegInfo", NET_EHOME_DEV_REG_INFO),
        ("struRegAddr", NET_EHOME_IPADDRESS),  # 设备注册的服务器地址
        ("sDevName", C_BYTE * MAX_DEVNAME_LEN_EX),
        ("byDeviceFullSerial", C_BYTE * MAX_FULL_SERIAL_NUM_LEN),
        ("byFirmwareIdenCode", C_BYTE * MAX_FIRMWARE_IDENT_CODE_LEN),
    ]


class NET_EHOME_ALARM_ISAPI_PICDATA(Structure):
    """通过 ISAPI 上传的报警图片。注意 pPicData 是真实可解引用的指针。"""

    _fields_ = [
        ("dwPicLen", C_DWORD),  # 图片长度
        ("byRes", C_BYTE * 4),
        ("szFilename", c_char * MAX_FILE_PATH_LEN),
        ("pPicData", POINTER(C_BYTE)),  # 图片数据指针
    ]


class NET_EHOME_ALARM_ISAPI_INFO(Structure):
    _fields_ = [
        ("pAlarmData", c_char_p),  # 报警数据（JSON 或 XML）
        ("dwAlarmDataLen", C_DWORD),
        ("byDataType", C_BYTE),  # 0-invalid,1-xml,2-json
        ("byPicturesNumber", C_BYTE),  # 图片数量
        ("byRes", C_BYTE * 2),
        ("pPicPackData", c_void_p),  # byPicturesNumber 个 NET_EHOME_ALARM_ISAPI_PICDATA
        ("byRes1", C_BYTE * 32),
    ]


class NET_EHOME_ALARM_MSG(Structure):
    """报警监听回调里拿到的数据。"""

    _fields_ = [
        ("dwAlarmType", C_DWORD),
        ("pAlarmInfo", c_void_p),  # 报警内容（结构体）
        ("dwAlarmInfoLen", C_DWORD),
        ("pXmlBuf", c_void_p),  # 报警内容（JSON/XML 原始串）
        ("dwXmlBufLen", C_DWORD),
        ("sSerialNumber", c_char * NET_EHOME_SERIAL_LEN),
        ("pHttpUrl", c_void_p),  # ISUP4.0「报警与图片不分离」时返回的 URL
        ("dwHttpUrlLen", C_DWORD),
        ("byRes", C_BYTE * 12),
    ]


# 设备注册回调：严禁在回调里调用其他 HCISUPSDK 接口
DEVICE_REGISTER_CB = fun_ctype(
    C_BOOL, C_LONG, C_DWORD, c_void_p, C_DWORD, c_void_p, C_DWORD, c_void_p
)

# 报警回调：同样严禁调用其他 SDK 接口、耗时 < 10ms
EHomeMsgCallBack = fun_ctype(C_BOOL, C_LONG, POINTER(NET_EHOME_ALARM_MSG), c_void_p)


class NET_EHOME_CMS_LISTEN_PARAM(Structure):
    _fields_ = [
        ("struAddress", NET_EHOME_IPADDRESS),  # 本地监听地址
        ("fnCB", DEVICE_REGISTER_CB),  # 设备注册回调
        ("pUserData", c_void_p),
        ("dwKeepAliveSec", C_DWORD),  # 心跳间隔秒，0=默认30
        ("dwTimeOutCount", C_DWORD),  # 心跳超时次数，0=默认3
        ("byRes", C_BYTE * 24),
    ]


class NET_EHOME_ALARM_LISTEN_PARAM(Structure):
    _fields_ = [
        ("struAddress", NET_EHOME_IPADDRESS),  # 本地监听地址
        ("fnMsgCb", EHomeMsgCallBack),  # 报警回调
        ("pUserData", c_void_p),
        ("byProtocolType", C_BYTE),  # 0-TCP 1-UDP 2-MQTT
        ("byUseCmsPort", C_BYTE),  # 是否复用 CMS 端口
        ("byUseThreadPool", C_BYTE),  # 0-用线程池回调 1-不用
        ("byRes1", C_BYTE),
        ("dwKeepAliveSec", C_DWORD),
        ("dwTimeOutCount", C_DWORD),
        ("byRes", C_BYTE * 20),
    ]


LPNET_EHOME_CMS_LISTEN_PARAM = POINTER(NET_EHOME_CMS_LISTEN_PARAM)
LPNET_EHOME_ALARM_LISTEN_PARAM = POINTER(NET_EHOME_ALARM_LISTEN_PARAM)
LPNET_EHOME_ALARM_ISAPI_INFO = POINTER(NET_EHOME_ALARM_ISAPI_INFO)
LPNET_EHOME_DEV_REG_INFO_V12 = POINTER(NET_EHOME_DEV_REG_INFO_V12)


# ---------------------------------------------------------------------------
# 载入 DLL
# ---------------------------------------------------------------------------
class ISUPSDKError(RuntimeError):
    def __init__(self, message, error_code=None):
        self.error_code = error_code
        super().__init__(
            message if error_code is None else f"{message} (错误码 {error_code})"
        )


def _ensure_libs():
    missing = [
        name for name in _DLL_NAMES[sys_platform].values()
        if not os.path.isfile(os.path.join(LIB_DIR, name))
    ]
    if missing:
        raise FileNotFoundError(
            f"lib_isup 目录缺少 {'、'.join(missing)}，请先运行: python setup_libs.py"
        )


# SDK 内部会用 LoadLibrary("zlib1.dll") 这类**不带路径**的方式加载依赖，
# 走的是进程的 DLL 搜索路径。如果不把 lib_isup 加进去，会报
#   HPR_LoadDSo Failed, Path[zlib1.dll] syserror[126]  (126 = 找不到模块)
# 这里在加载 HCISUP*.dll 之前把 lib_isup 注册成 DLL 搜索目录。
_DLL_DIR_HANDLES = []


def _register_dll_directory():
    if sys_platform != "windows":
        return
    if not os.path.isdir(LIB_DIR):
        return
    # os.add_dll_directory 需要保持 handle 存活，否则会被回收
    try:
        handle = os.add_dll_directory(LIB_DIR)
        _DLL_DIR_HANDLES.append(handle)
    except (AttributeError, OSError):
        # 老 Python 没有这个 API，退回改 PATH
        os.environ["PATH"] = LIB_DIR + os.pathsep + os.environ.get("PATH", "")


class ISUPSDK:
    """ISUP SDK 的封装：CMS（设备注册）+ Alarm（报警监听）。"""

    def __init__(self, log_dir=None):
        _ensure_libs()
        _register_dll_directory()
        self.log_dir = log_dir or os.path.join(BASE_DIR, "IsupLog_Python")
        os.makedirs(self.log_dir, exist_ok=True)

        self.alarm = load_library(_lib_path("alarm"))
        self.cms = load_library(_lib_path("cms"))

    # 已知无害告警：SDK 内部会尝试 LoadLibrary("zlib1.dll")（不带路径），
    # 报 HPR_LoadDSo Failed syserror[126]。实测 lib_isup\zlib1.dll 本身是好的
    # （x64、依赖齐全、显式路径能加载成功），SDK 只是没在它的搜索路径里找到。
    # zlib 只用于压缩类业务，收报警/图片不需要，日志里忽略这条即可。
        self._bind_prototypes()

        self.cms_listen_handle = -1
        self.alarm_listen_handle = -1
        # 必须持有回调引用，否则会被 GC 回收导致崩溃
        self._register_cb = None
        self._alarm_cb = None

    # -- 原型绑定 ---------------------------------------------------------
    def _bind_prototypes(self):
        a, c = self.alarm, self.cms

        c.NET_ECMS_Init.restype = C_BOOL
        c.NET_ECMS_Fini.restype = C_BOOL
        c.NET_ECMS_SetSDKInitCfg.restype = C_BOOL
        c.NET_ECMS_SetSDKInitCfg.argtypes = [c_int, c_void_p]
        c.NET_ECMS_SetSDKLocalCfg.restype = C_BOOL
        c.NET_ECMS_SetSDKLocalCfg.argtypes = [c_int, c_void_p]
        c.NET_ECMS_GetLastError.restype = C_DWORD
        c.NET_ECMS_GetBuildVersion.restype = C_DWORD
        c.NET_ECMS_StartListen.restype = C_LONG
        c.NET_ECMS_StartListen.argtypes = [LPNET_EHOME_CMS_LISTEN_PARAM]
        c.NET_ECMS_StopListen.restype = C_BOOL
        c.NET_ECMS_StopListen.argtypes = [C_LONG]
        c.NET_ECMS_SetLogToFile.restype = C_BOOL
        c.NET_ECMS_SetLogToFile.argtypes = [C_DWORD, c_char_p, C_BOOL]

        a.NET_EALARM_Init.restype = C_BOOL
        a.NET_EALARM_Fini.restype = C_BOOL
        a.NET_EALARM_SetSDKInitCfg.restype = C_BOOL
        a.NET_EALARM_SetSDKInitCfg.argtypes = [c_int, c_void_p]
        a.NET_EALARM_SetSDKLocalCfg.restype = C_BOOL
        a.NET_EALARM_SetSDKLocalCfg.argtypes = [c_int, c_void_p]
        a.NET_EALARM_GetLastError.restype = C_DWORD
        a.NET_EALARM_GetBuildVersion.restype = C_DWORD
        a.NET_EALARM_StartListen.restype = C_LONG
        a.NET_EALARM_StartListen.argtypes = [LPNET_EHOME_ALARM_LISTEN_PARAM]
        a.NET_EALARM_StopListen.restype = C_BOOL
        a.NET_EALARM_StopListen.argtypes = [C_LONG]
        a.NET_EALARM_SetLogToFile.restype = C_BOOL
        a.NET_EALARM_SetLogToFile.argtypes = [C_DWORD, c_char_p, C_BOOL]

    # -- 初始化 -----------------------------------------------------------
    def set_openssl_paths(self, libeay_path, ssleay_path):
        """ISUP 依赖 OpenSSL 1.0.x 的 libeay32/ssleay32，必须在 Init 之前设置。"""
        libeay = str(libeay_path).encode("utf-8")
        ssleay = str(ssleay_path).encode("utf-8")
        if not self.cms.NET_ECMS_SetSDKInitCfg(
            NET_EHOME_CMS_INIT_CFG_LIBEAY_PATH, c_char_p(libeay)
        ):
            raise ISUPSDKError(
                "NET_ECMS_SetSDKInitCfg(LIBEAY) 失败", self.cms.NET_ECMS_GetLastError()
            )
        if not self.cms.NET_ECMS_SetSDKInitCfg(
            NET_EHOME_CMS_INIT_CFG_SSLEAY_PATH, c_char_p(ssleay)
        ):
            raise ISUPSDKError(
                "NET_ECMS_SetSDKInitCfg(SSLEAY) 失败", self.cms.NET_ECMS_GetLastError()
            )
        if not self.alarm.NET_EALARM_SetSDKInitCfg(
            NET_EHOME_EALARM_INIT_CFG_LIBEAY_PATH, c_char_p(libeay)
        ):
            raise ISUPSDKError(
                "NET_EALARM_SetSDKInitCfg(LIBEAY) 失败",
                self.alarm.NET_EALARM_GetLastError(),
            )
        if not self.alarm.NET_EALARM_SetSDKInitCfg(
            NET_EHOME_EALARM_INIT_CFG_SSLEAY_PATH, c_char_p(ssleay)
        ):
            raise ISUPSDKError(
                "NET_EALARM_SetSDKInitCfg(SSLEAY) 失败",
                self.alarm.NET_EALARM_GetLastError(),
            )

    def init(self, log_level=3, auto_del_log=False):
        if not self.cms.NET_ECMS_Init():
            raise ISUPSDKError("NET_ECMS_Init 失败", self.cms.NET_ECMS_GetLastError())
        if not self.alarm.NET_EALARM_Init():
            raise ISUPSDKError(
                "NET_EALARM_Init 失败", self.alarm.NET_EALARM_GetLastError()
            )
        self.cms.NET_ECMS_SetLogToFile(
            log_level, self.log_dir.encode("utf-8"), bool(auto_del_log)
        )
        self.alarm.NET_EALARM_SetLogToFile(
            log_level, self.log_dir.encode("utf-8"), bool(auto_del_log)
        )

    def fini(self):
        self.stop_listen()
        try:
            self.alarm.NET_EALARM_Fini()
        except Exception:
            pass
        try:
            self.cms.NET_ECMS_Fini()
        except Exception:
            pass

    # -- 本地配置 ---------------------------------------------------------
    def _set_local_cfg(self, lib, lib_label, cfg_type, cfg_ptr):
        """CMS 用 NET_ECMS_SetSDKLocalCfg，EALARM 用 NET_EALARM_SetSDKLocalCfg。"""
        setter = (
            lib.NET_ECMS_SetSDKLocalCfg
            if lib_label == "CMS"
            else lib.NET_EALARM_SetSDKLocalCfg
        )
        if not setter(cfg_type, cfg_ptr):
            getter = lib.NET_ECMS_GetLastError if lib_label == "CMS" else lib.NET_EALARM_GetLastError
            raise ISUPSDKError(f"{lib_label} 本地配置失败", getter())

    def set_access_security(self, mode=2):
        """设置设备主动接入的安全模式。

        mode: 0-兼容模式(任意版本都能接) 1-普通模式(仅4.0以下) 2-安全模式(仅4.0以上)
        设备是 ISUP 4.0/5.0 时用 2；不确定阶段先用 0，避免设备连不上。
        """
        cfg = NET_EHOME_LOCAL_ACCESS_SECURITY()
        cfg.dwSize = sizeof(cfg)
        cfg.byAccessSecurity = mode
        self._set_local_cfg(self.cms, "CMS", ACTIVE_ACCESS_SECURITY, byref(cfg))
        self._set_local_cfg(self.alarm, "EALARM", ACTIVE_ACCESS_SECURITY, byref(cfg))

    def set_register_listen_mode(self, mode=REGISTER_LISTEN_MODE_ALL):
        cfg = NET_EHOME_REGISTER_LISTEN_MODE()
        cfg.dwSize = sizeof(cfg)
        cfg.dwRegisterListenMode = mode
        self._set_local_cfg(self.cms, "CMS", REGISTER_LISTEN_MODE, byref(cfg))

    # -- 监听 -------------------------------------------------------------
    def start_cms_listen(self, ip, port, register_cb, user_data=None,
                         keep_alive_sec=30, timeout_count=3):
        param = NET_EHOME_CMS_LISTEN_PARAM()
        param.struAddress.szIP = str(ip).encode("utf-8")
        param.struAddress.wPort = int(port)
        self._register_cb = register_cb
        param.fnCB = register_cb
        param.pUserData = user_data
        param.dwKeepAliveSec = int(keep_alive_sec)
        param.dwTimeOutCount = int(timeout_count)

        handle = self.cms.NET_ECMS_StartListen(byref(param))
        if handle < 0:
            raise ISUPSDKError(
                f"NET_ECMS_StartListen 失败 (监听 {ip}:{port})",
                self.cms.NET_ECMS_GetLastError(),
            )
        self.cms_listen_handle = handle
        return handle

    def start_alarm_listen(self, ip, port, msg_cb, user_data=None,
                           protocol_type=PROTOCOL_TCP, use_cms_port=False,
                           use_thread_pool=False, keep_alive_sec=30, timeout_count=3):
        param = NET_EHOME_ALARM_LISTEN_PARAM()
        param.struAddress.szIP = str(ip).encode("utf-8")
        param.struAddress.wPort = int(port)
        self._alarm_cb = msg_cb
        param.fnMsgCb = msg_cb
        param.pUserData = user_data
        param.byProtocolType = protocol_type
        param.byUseCmsPort = 1 if use_cms_port else 0
        # 头文件：0-回调使用线程池，1-不使用线程池
        param.byUseThreadPool = 1 if use_thread_pool else 0
        param.dwKeepAliveSec = int(keep_alive_sec)
        param.dwTimeOutCount = int(timeout_count)

        handle = self.alarm.NET_EALARM_StartListen(byref(param))
        if handle < 0:
            raise ISUPSDKError(
                f"NET_EALARM_StartListen 失败 (监听 {ip}:{port})",
                self.alarm.NET_EALARM_GetLastError(),
            )
        self.alarm_listen_handle = handle
        return handle

    def stop_listen(self):
        if self.alarm_listen_handle >= 0:
            try:
                self.alarm.NET_EALARM_StopListen(self.alarm_listen_handle)
            except Exception:
                pass
            self.alarm_listen_handle = -1
        if self.cms_listen_handle >= 0:
            try:
                self.cms.NET_ECMS_StopListen(self.cms_listen_handle)
            except Exception:
                pass
            self.cms_listen_handle = -1

    def get_versions(self):
        def unpack(value):
            return ".".join(
                str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0)
            )

        return {
            "cms": unpack(self.cms.NET_ECMS_GetBuildVersion()),
            "alarm": unpack(self.alarm.NET_EALARM_GetBuildVersion()),
        }


# ---------------------------------------------------------------------------
# 字节解析小工具（回调里只做拷贝，解析放到别的线程）
# ---------------------------------------------------------------------------
def bytes_from_ptr(value, length):
    """把指针 + 长度安全地拷成 bytes，避免读到越界内容。"""
    if not value or not length:
        return b""
    return string_at(value, int(length))


def pick_ssl_dll_names(lib_dir):
    """ISUP 用的是 OpenSSL 1.0.x：libeay32.dll / ssleay32.dll。"""
    candidates = [
        ("libeay32.dll", "ssleay32.dll"),
        ("libcrypto-1_1-x64.dll", "libssl-1_1-x64.dll"),
        ("libcrypto-3-x64.dll", "libssl-3-x64.dll"),
    ]
    for libeay, ssleay in candidates:
        if os.path.isfile(os.path.join(lib_dir, libeay)) and os.path.isfile(
            os.path.join(lib_dir, ssleay)
        ):
            return os.path.join(lib_dir, libeay), os.path.join(lib_dir, ssleay)
    raise FileNotFoundError(
        "lib_isup 目录缺少 OpenSSL 动态库（libeay32.dll/ssleay32.dll），"
        "请先运行: python setup_libs.py"
    )
