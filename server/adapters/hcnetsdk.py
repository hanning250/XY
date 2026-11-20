# -*- coding: utf-8 -*-
"""HCNetSDK（设备网路 SDK）ctypes 绑定 —— 只覆盖登录 / 布防 / ISAPI 报警。

头文件在 lib/hcnetsdk/include/HCNetSDK.h（运行只加载 lib/hcnetsdk/*.so）。
Python 不编译 .h，结构体按该头文件和官方「报警布防」Demo 对齐。
"""

from __future__ import annotations

import ctypes
from ctypes import POINTER, Structure, c_bool, c_char, c_uint, c_ulonglong, c_ushort, c_void_p, c_ubyte

# Linux x86_64：与官方 Python Demo 一致
C_BYTE = c_ubyte
C_WORD = c_ushort
C_DWORD = c_uint
C_LONG = ctypes.c_int
C_UINT64 = c_ulonglong
C_BOOL = ctypes.c_int
C_LPVOID = c_void_p

COMM_ISAPI_ALARM = 0x6009
COMM_ALARM_V30 = 0x4000

NET_SDK_INIT_CFG_SDK_PATH = 2
NET_SDK_INIT_CFG_LIBEAY_PATH = 3
NET_SDK_INIT_CFG_SSLEAY_PATH = 4
NET_DVR_LOCAL_CFG_TYPE_GENERAL = 17


class NET_DVR_DEVICEINFO_V30(Structure):
    _fields_ = [
        ("sSerialNumber", C_BYTE * 48),
        ("byAlarmInPortNum", C_BYTE),
        ("byAlarmOutPortNum", C_BYTE),
        ("byDiskNum", C_BYTE),
        ("byDVRType", C_BYTE),
        ("byChanNum", C_BYTE),
        ("byStartChan", C_BYTE),
        ("byAudioChanNum", C_BYTE),
        ("byIPChanNum", C_BYTE),
        ("byZeroChanNum", C_BYTE),
        ("byMainProto", C_BYTE),
        ("bySubProto", C_BYTE),
        ("bySupport", C_BYTE),
        ("bySupport1", C_BYTE),
        ("bySupport2", C_BYTE),
        ("wDevType", C_WORD),
        ("bySupport3", C_BYTE),
        ("byMultiStreamProto", C_BYTE),
        ("byStartDChan", C_BYTE),
        ("byStartDTalkChan", C_BYTE),
        ("byHighDChanNum", C_BYTE),
        ("bySupport4", C_BYTE),
        ("byLanguageType", C_BYTE),
        ("byVoiceInChanNum", C_BYTE),
        ("byStartVoiceInChanNo", C_BYTE),
        ("bySupport5", C_BYTE),
        ("bySupport6", C_BYTE),
        ("byMirrorChanNum", C_BYTE),
        ("wStartMirrorChanNo", C_WORD),
        ("bySupport7", C_BYTE),
        ("byRes2", C_BYTE),
    ]


fLoginResultCallBack = ctypes.CFUNCTYPE(None, C_LONG, C_DWORD, POINTER(NET_DVR_DEVICEINFO_V30), c_void_p)


class NET_DVR_DEVICEINFO_V40(Structure):
    _fields_ = [
        ("struDeviceV30", NET_DVR_DEVICEINFO_V30),
        ("bySupportLock", C_BYTE),
        ("byRetryLoginTime", C_BYTE),
        ("byPasswordLevel", C_BYTE),
        ("byProxyType", C_BYTE),
        ("dwSurplusLockTime", C_DWORD),
        ("byCharEncodeType", C_BYTE),
        ("bySupportDev5", C_BYTE),
        ("bySupport", C_BYTE),
        ("byLoginMode", C_BYTE),
        ("dwOEMCode", C_DWORD),
        ("iResidualValidity", C_LONG),
        ("byResidualValidity", C_BYTE),
        ("bySingleStartDTalkChan", C_BYTE),
        ("bySingleDTalkChanNums", C_BYTE),
        ("byPassWordResetLevel", C_BYTE),
        ("bySupportStreamEncrypt", C_BYTE),
        ("byMarketType", C_BYTE),
        ("byRes2", C_BYTE * 238),
    ]


class NET_DVR_USER_LOGIN_INFO(Structure):
    _fields_ = [
        ("sDeviceAddress", c_char * 129),
        ("byUseTransport", C_BYTE),
        ("wPort", C_WORD),
        ("sUserName", c_char * 64),
        ("sPassword", c_char * 64),
        ("cbLoginResult", fLoginResultCallBack),
        ("pUser", C_LPVOID),
        ("bUseAsynLogin", C_DWORD),
        ("byProxyType", C_BYTE),
        ("byUseUTCTime", C_BYTE),
        ("byLoginMode", C_BYTE),  # 0-Private 1-ISAPI 2-自适应
        ("byHttps", C_BYTE),
        ("iProxyID", C_DWORD),
        ("byVerifyMode", C_BYTE),
        ("byRes2", C_BYTE * 119),
    ]


class NET_DVR_LOCAL_SDK_PATH(Structure):
    _fields_ = [
        ("sPath", c_char * 256),
        ("byRes", C_BYTE * 128),
    ]


class NET_DVR_ALARMER(Structure):
    _fields_ = [
        ("byUserIDValid", C_BYTE),
        ("bySerialValid", C_BYTE),
        ("byVersionValid", C_BYTE),
        ("byDeviceNameValid", C_BYTE),
        ("byMacAddrValid", C_BYTE),
        ("byLinkPortValid", C_BYTE),
        ("byDeviceIPValid", C_BYTE),
        ("bySocketIPValid", C_BYTE),
        ("lUserID", C_LONG),
        ("sSerialNumber", C_BYTE * 48),
        ("dwDeviceVersion", C_DWORD),
        ("sDeviceName", C_BYTE * 32),
        ("byMacAddr", C_BYTE * 6),
        ("wLinkPort", C_WORD),
        ("sDeviceIP", C_BYTE * 128),
        ("sSocketIP", C_BYTE * 128),
        ("byIpProtocol", C_BYTE),
        ("byRes2", C_BYTE * 11),
    ]


LPNET_DVR_ALARMER = POINTER(NET_DVR_ALARMER)


class NET_DVR_SETUPALARM_PARAM(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("byLevel", C_BYTE),
        ("byAlarmInfoType", C_BYTE),
        ("byRetAlarmTypeV40", C_BYTE),
        ("byRetDevInfoVersion", C_BYTE),
        ("byRetVQDAlarmType", C_BYTE),
        ("byFaceAlarmDetection", C_BYTE),
        ("bySupport", C_BYTE),
        ("byBrokenNetHttp", C_BYTE),
        ("wTaskNo", C_WORD),
        ("byDeployType", C_BYTE),
        ("byRes1", C_BYTE * 3),
        ("byAlarmTypeURL", C_BYTE),
        ("byCustomCtrl", C_BYTE),
    ]


class NET_DVR_ALARM_ISAPI_PICDATA(Structure):
    _fields_ = [
        ("dwPicLen", C_DWORD),
        ("byPicType", C_BYTE),
        ("byRes", C_BYTE * 3),
        ("szFilename", c_char * 256),
        ("pPicData", POINTER(C_BYTE)),
    ]


class NET_DVR_ALARM_ISAPI_INFO(Structure):
    _fields_ = [
        ("pAlarmData", c_void_p),
        ("dwAlarmDataLen", C_DWORD),
        ("byDataType", C_BYTE),
        ("byPicturesNumber", C_BYTE),
        ("byRes", C_BYTE * 2),
        ("pPicPackData", c_void_p),
        ("byRes1", C_BYTE * 32),
    ]


LPNET_DVR_ALARM_ISAPI_INFO = POINTER(NET_DVR_ALARM_ISAPI_INFO)


class NET_DVR_LOCAL_GENERAL_CFG(Structure):
    _fields_ = [
        ("byExceptionCbDirectly", C_BYTE),
        ("byNotSplitRecordFile", C_BYTE),
        ("byResumeUpgradeEnable", C_BYTE),
        ("byAlarmJsonPictureSeparate", C_BYTE),
        ("byRes", C_BYTE * 4),
        ("i64FileSize", C_UINT64),
        ("dwResumeUpgradeTimeout", C_DWORD),
        ("byAlarmReconnectMode", C_BYTE),
        ("byStdXmlBufferSize", C_BYTE),
        ("byMultiplexing", C_BYTE),
        ("byFastUpgrade", C_BYTE),
        ("byRes1", C_BYTE * 232),
    ]


# BOOL CALLBACK(LONG lCommand, NET_DVR_ALARMER*, char* pAlarmInfo, DWORD dwBufLen, void* pUser)
MSGCallBack_V31 = ctypes.CFUNCTYPE(
    c_bool, C_LONG, LPNET_DVR_ALARMER, c_void_p, C_DWORD, c_void_p
)

# ---- 预览取流（RealPlay → PlayCtrl）----
NET_DVR_SYSHEAD = 1
NET_DVR_STREAMDATA = 2


class NET_DVR_PREVIEWINFO(Structure):
    _fields_ = [
        ("lChannel", C_LONG),
        ("dwStreamType", C_DWORD),  # 0 主码流 1 子码流
        ("dwLinkMode", C_DWORD),  # 0 TCP
        ("hPlayWnd", C_DWORD),  # Linux HWND=uint；0=不解码显示，只回调码流
        ("bBlocked", C_DWORD),
        ("bPassbackRecord", C_DWORD),
        ("byPreviewMode", C_BYTE),
        ("byStreamID", C_BYTE * 32),
        ("byProtoType", C_BYTE),
        ("byRes1", C_BYTE),
        ("byVideoCodingType", C_BYTE),
        ("dwDisplayBufNum", C_DWORD),
        ("byNPQMode", C_BYTE),
        ("byRecvMetaData", C_BYTE),
        ("byDataType", C_BYTE),
        ("byReconnect", C_BYTE),
        ("byRes", C_BYTE * 212),
    ]


# void CALLBACK(LONG lPlayHandle, DWORD dwDataType, BYTE* pBuffer, DWORD dwBufSize, void* pUser)
REALDATACALLBACK = ctypes.CFUNCTYPE(
    None, C_LONG, C_DWORD, POINTER(C_BYTE), C_DWORD, c_void_p
)
