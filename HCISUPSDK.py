# -*- coding: utf-8 -*-
"""HCISUP SDK ctypes bindings (CMS + Alarm modules)."""
import os
import platform
import sys
from ctypes import *
from enum import IntEnum

MAX_DEVICE_ID_LEN = 256
NET_EHOME_SERIAL_LEN = 12
MAX_MASTER_KEY_LEN = 16
MAX_FILE_PATH_LEN = 256
MAX_TIME_LEN = 32
MAX_URL_LEN = 512

C_BOOL = c_int
C_BYTE = c_ubyte
C_DWORD = c_uint32
C_LONG = c_int32
C_WORD = c_uint16


class RegisterType(IntEnum):
    ENUM_DEV_ON = 0
    ENUM_DEV_OFF = 1
    ENUM_DEV_ADDRESS_CHANGED = 2
    ENUM_DEV_AUTH = 3
    ENUM_DEV_SESSIONKEY = 4
    ENUM_DEV_DAS_REQ = 5
    ENUM_DEV_SESSIONKEY_REQ = 6
    ENUM_DEV_DAS_REREGISTER = 7
    ENUM_DEV_DAS_PINGREO = 8
    ENUM_DEV_DAS_EHOMEKEY_ERROR = 9
    ENUM_DEV_SESSIONKEY_ERROR = 10
    ENUM_DEV_SLEEP = 11


class AlarmType(IntEnum):
    EHOME_ALARM = 1
    EHOME_ALARM_NOTICE_PICURL = 6
    EHOME_ISAPI_ALARM = 13


class LocalCfgType(IntEnum):
    ACTIVE_ACCESS_SECURITY = 0
    AMS_ADDRESS = 1
    LOCAL_CFG_TYPE_GENERAL = 4
    REGISTER_LISTEN_MODE = 8


class CmsInitCfgType(IntEnum):
    NET_EHOME_CMS_INIT_CFG_LIBEAY_PATH = 0
    NET_EHOME_CMS_INIT_CFG_SSLEAY_PATH = 1


class AlarmInitCfgType(IntEnum):
    NET_EHOME_EALARM_INIT_CFG_LIBEAY_PATH = 0
    NET_EHOME_EALARM_INIT_CFG_SSLEAY_PATH = 1


class NET_EHOME_IPADDRESS(Structure):
    _fields_ = [
        ("szIP", c_char * 128),
        ("wPort", C_WORD),
        ("byRes", C_BYTE * 2),
    ]


class NET_EHOME_DEV_REG_INFO(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("dwNetUnitType", C_DWORD),
        ("byDeviceID", C_BYTE * MAX_DEVICE_ID_LEN),
        ("byFirmwareVersion", C_BYTE * 24),
        ("struDevAdd", NET_EHOME_IPADDRESS),
        ("dwDevType", C_DWORD),
        ("dwManufacture", C_DWORD),
        ("byPassWord", C_BYTE * 32),
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
        ("struRegAddr", NET_EHOME_IPADDRESS),
        ("sDevName", C_BYTE * 64),
        ("byDeviceFullSerial", C_BYTE * 64),
        ("byFirmwareIdenCode", C_BYTE * 128),
    ]


class NET_EHOME_BLACKLIST_SEVER(Structure):
    _fields_ = [
        ("struAdd", NET_EHOME_IPADDRESS),
        ("byServerName", C_BYTE * 32),
        ("byUserName", C_BYTE * 32),
        ("byPassWord", C_BYTE * 32),
        ("byRes", C_BYTE * 64),
    ]


class NET_EHOME_SERVER_INFO_V50(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("dwKeepAliveSec", C_DWORD),
        ("dwTimeOutCount", C_DWORD),
        ("struTCPAlarmSever", NET_EHOME_IPADDRESS),
        ("struUDPAlarmSever", NET_EHOME_IPADDRESS),
        ("dwAlarmServerType", C_DWORD),
        ("struNTPSever", NET_EHOME_IPADDRESS),
        ("dwNTPInterval", C_DWORD),
        ("struPictureSever", NET_EHOME_IPADDRESS),
        ("dwPicServerType", C_DWORD),
        ("struBlackListServer", NET_EHOME_BLACKLIST_SEVER),
        ("struRedirectSever", NET_EHOME_IPADDRESS),
        ("byClouldAccessKey", C_BYTE * 64),
        ("byClouldSecretKey", C_BYTE * 64),
        ("byClouldHttps", C_BYTE),
        ("byRes1", C_BYTE * 3),
        ("dwAlarmKeepAliveSec", C_DWORD),
        ("dwAlarmTimeOutCount", C_DWORD),
        ("dwClouldPoolId", C_DWORD),
        ("byChildDeviceFlag", C_BYTE),
        ("byRes", C_BYTE * 367),
    ]


class NET_EHOME_DEV_SESSIONKEY(Structure):
    _fields_ = [
        ("sDeviceID", C_BYTE * MAX_DEVICE_ID_LEN),
        ("sSessionKey", C_BYTE * MAX_MASTER_KEY_LEN),
    ]


class NET_EHOME_ALARM_MSG(Structure):
    _fields_ = [
        ("dwAlarmType", C_DWORD),
        ("pAlarmInfo", c_void_p),
        ("dwAlarmInfoLen", C_DWORD),
        ("pXmlBuf", c_void_p),
        ("dwXmlBufLen", C_DWORD),
        ("sSerialNumber", c_char * NET_EHOME_SERIAL_LEN),
        ("pHttpUrl", c_void_p),
        ("dwHttpUrlLen", C_DWORD),
        ("byRes", C_BYTE * 12),
    ]


DEVICE_REGISTER_CB = CFUNCTYPE(
    C_BOOL, C_LONG, C_DWORD, c_void_p, C_DWORD, c_void_p, C_DWORD, c_void_p
)
EHomeMsgCallBack = CFUNCTYPE(C_BOOL, C_LONG, POINTER(NET_EHOME_ALARM_MSG), c_void_p)


class NET_EHOME_CMS_LISTEN_PARAM(Structure):
    _fields_ = [
        ("struAddress", NET_EHOME_IPADDRESS),
        ("fnCB", DEVICE_REGISTER_CB),
        ("pUserData", c_void_p),
        ("dwKeepAliveSec", C_DWORD),
        ("dwTimeOutCount", C_DWORD),
        ("byRes", C_BYTE * 24),
    ]


class NET_EHOME_ALARM_ISAPI_PICDATA(Structure):
    _fields_ = [
        ("dwPicLen", C_DWORD),
        ("byRes", C_BYTE * 4),
        ("szFilename", c_char * MAX_FILE_PATH_LEN),
        ("pPicData", c_void_p),
    ]


class NET_EHOME_NOTICE_PICURL(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("byDeviceID", C_BYTE * MAX_DEVICE_ID_LEN),
        ("wPicType", C_WORD),
        ("wAlarmType", C_WORD),
        ("dwAlarmChan", C_DWORD),
        ("byAlarmTime", c_char * MAX_TIME_LEN),
        ("dwCaptureChan", C_DWORD),
        ("byPicTime", c_char * MAX_TIME_LEN),
        ("byPicUrl", c_char * MAX_URL_LEN),
        ("dwManualSnapSeq", C_DWORD),
        ("byRetransFlag", C_BYTE),
        ("byTimeDiffH", C_BYTE),
        ("byTimeDiffM", C_BYTE),
        ("byRes", C_BYTE * 29),
    ]


class NET_EHOME_ALARM_ISAPI_INFO(Structure):
    _fields_ = [
        ("pAlarmData", c_char_p),
        ("dwAlarmDataLen", C_DWORD),
        ("byDataType", C_BYTE),
        ("byPicturesNumber", C_BYTE),
        ("byRes", C_BYTE * 2),
        ("pPicPackData", c_void_p),
        ("byRes1", C_BYTE * 32),
    ]


class NET_EHOME_ALARM_LISTEN_PARAM(Structure):
    _fields_ = [
        ("struAddress", NET_EHOME_IPADDRESS),
        ("fnMsgCb", EHomeMsgCallBack),
        ("pUserData", c_void_p),
        ("byProtocolType", C_BYTE),
        ("byUseCmsPort", C_BYTE),
        ("byUseThreadPool", C_BYTE),
        ("byRes1", C_BYTE),
        ("dwKeepAliveSec", C_DWORD),
        ("dwTimeOutCount", C_DWORD),
        ("byRes", C_BYTE * 20),
    ]


class NET_EHOME_LOCAL_ACCESS_SECURITY(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("byAccessSecurity", C_BYTE),
        ("byRes", C_BYTE * 127),
    ]


class NET_EHOME_LOCAL_GENERAL_CFG(Structure):
    _fields_ = [
        ("byAlarmPictureSeparate", C_BYTE),
        ("byRes", C_BYTE * 127),
    ]


class NET_EHOME_AMS_ADDRESS(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("byEnable", C_BYTE),
        ("byRes1", C_BYTE * 3),
        ("struAddress", NET_EHOME_IPADDRESS),
        ("byRes2", C_BYTE * 32),
    ]


class NET_EHOME_REGISTER_LISTEN_MODE(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("dwRegisterListenMode", C_DWORD),
        ("byRes", C_BYTE * 128),
    ]


sys_platform = platform.system().lower()
_lib_dir = os.path.join(os.path.dirname(__file__), "lib")


def _pick_ssl_dll_names(lib_dir):
    candidates = [
        ("libeay32.dll", "ssleay32.dll"),
        ("libcrypto-1_1-x64.dll", "libssl-1_1-x64.dll"),
        ("libcrypto-3-x64.dll", "libssl-3-x64.dll"),
    ]
    for crypto_name, ssl_name in candidates:
        if os.path.isfile(os.path.join(lib_dir, crypto_name)) and os.path.isfile(
            os.path.join(lib_dir, ssl_name)
        ):
            return crypto_name, ssl_name
    raise FileNotFoundError(
        f"lib 目录缺少 OpenSSL DLL，请先运行: python setup_isup_libs.py ({lib_dir})"
    )


def prepare_runtime_env():
    """确保 HCISUP 依赖 DLL（含 zlib1.dll）可被加载。"""
    os.makedirs(_lib_dir, exist_ok=True)
    if sys_platform == "windows":
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_lib_dir)
        os.environ["PATH"] = _lib_dir + os.pathsep + os.environ.get("PATH", "")


def load_cms_dll():
    prepare_runtime_env()
    path = os.path.join(_lib_dir, "HCISUPCMS.dll")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"未找到 {path}，请先运行 setup_isup_libs.py")
    return cdll.LoadLibrary(path)


def load_alarm_dll():
    prepare_runtime_env()
    path = os.path.join(_lib_dir, "HCISUPAlarm.dll")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"未找到 {path}，请先运行 setup_isup_libs.py")
    return cdll.LoadLibrary(path)


def configure_sdk_paths(dll, init_cfg_enum, lib_dir):
    crypto_name, ssl_name = _pick_ssl_dll_names(lib_dir)
    if sys_platform == "windows":
        lib_path = lib_dir.encode("gbk")
    else:
        lib_path = lib_dir.encode("utf-8")
    dll.NET_ECMS_SetSDKInitCfg = dll.NET_ECMS_SetSDKInitCfg
    # Alarm DLL uses NET_EALARM_SetSDKInitCfg — configured separately in service.


def bytes_to_str(raw, encoding="utf-8"):
    if raw is None:
        return ""
    if isinstance(raw, (bytes, bytearray)):
        return raw.split(b"\x00")[0].decode(encoding, errors="ignore").strip()
    return str(raw).strip()
