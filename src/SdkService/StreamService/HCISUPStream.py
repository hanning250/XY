# -*- coding: utf-8 -*-
# @Time : 2023/9/8 11:02
# @Author : qiu jiahang

# 宏定义
from ctypes import Structure, c_void_p, c_bool, POINTER, c_char, Union
from enum import Enum

from src.SdkService.CmsService.HCISUPCMS import target_dir, system_type, C_BYTE, NET_EHOME_IPADDRESS, fun_ctype, C_LONG, \
    C_DWORD, C_WORD, NET_EHOME_TIME

sms_sdkdllpath_dict = {'windows64': target_dir + '\\lib\\' + 'HCISUPStream.dll',
                       'windows32': target_dir + '\\lib\\' + 'HCISUPStream.dll',
                       'linux64': target_dir + '/lib/libHCISUPStream.so',
                       'linux32': target_dir + '/lib/libHCISUPStream.so'}
sms_sdkdllpath = sms_sdkdllpath_dict[system_type]

NET_EHOME_SYSHEAD = 1  # 系统头数据
NET_EHOME_STREAMDATA = 2  # 视频流数据（包括复合流和音视频分开的视频流数据）
NET_EHOME_STREAMEND = 3  # 视频流结束标记


# 枚举流媒体服务器的初始化配置类型。
class NET_EHOME_ESTREAM_INIT_CFG_TYPE(Enum):
    NET_EHOME_ESTREAM_INIT_CFG_LIBEAY_PATH = 0  # 设置OpenSSL的libeay32.dll / libcrypto.so所在路径
    NET_EHOME_ESTREAM_INIT_CFG_SSLEAY_PATH = 1  # 设置OpenSSL的ssleay32.dll / libssl.so所在路径
    NET_EHOME_ESTREAM_INIT_CFG_USERCERTIFICATE_PATH = 2  # 设置TLS监听和DTLS监听的服务器证书路径，TLS和DTLS复用同一个证书
    NET_EHOME_ESTREAM_INIT_CFG_USERPRIVATEKEY_PATH = 3  # 设置TLS监听和DTLS监听的私钥证书路径，TLS和DTLS复用同一个证书


# 预览请求参数结构体（适用于 64 位 Windows 或 Linux 操作系统）
class NET_EHOME_NEWLINK_CB_MSG(Structure):
    _fields_ = [
        ('szDeviceID', C_BYTE * 256),  # 设备标示符(出参)
        ('iSessionID', C_LONG),  # 设备分配给该取流会话的ID(出参)
        ('dwChannelNo', C_DWORD),  # 设备通道号(出参)
        ('byStreamType', C_BYTE),  # 0-主码流，1-子码流(出参)
        ('byRes1', C_BYTE * 2),
        ('byStreamFormat', C_BYTE),  # 封装格式：0- PS,1-标准流(入参), 2-原始码流(即设备给什么流获取到的就是什么流)
        ('sDeviceSerial', c_char * 12),  # 设备序列号，数字序列号(出参)
        ('byRes', C_BYTE * 112),
    ]


# 接收预览请求响应的回调函数
PREVIEW_NEWLINK_CB = fun_ctype(c_bool, C_LONG, POINTER(NET_EHOME_NEWLINK_CB_MSG), POINTER(c_void_p))


# 预览监听参数结构体
class NET_EHOME_LISTEN_PREVIEW_CFG(Structure):
    _fields_ = [
        ('struIPAdress', NET_EHOME_IPADDRESS),  # 本地监听信息，IP为0.0.0.0的情况下，默认为本地地址，多个网卡的情况下，默认为从操作系统获取到的第一个
        ('fnNewLinkCB', PREVIEW_NEWLINK_CB),  # 预览请求回调函数，当收到预览连接请求后，SDK会回调该回调函数。
        ('pUser', c_void_p),  # 用户参数，在fnNewLinkCB中返回出来
        ('byLinkMode', C_BYTE),  # 0：TCP，1：UDP 2: HRUDP方式
        ('byRes', C_BYTE * 127),
    ]


# 预览回调数据结构体
class NET_EHOME_PREVIEW_CB_MSG(Structure):
    _fields_ = [
        ('byDataType', C_BYTE),  # NET_DVR_SYSHEAD(1)-码流头，NET_DVR_STREAMDATA(2)-码流数据
        ('byRes1', C_BYTE * 3),  # 保留
        ('pRecvdata', c_void_p),  # 码流头或者数据
        ('dwDataLen', C_DWORD),  # 数据长度
        ('byRes2', C_BYTE * 128),
    ]


LPNET_EHOME_PREVIEW_CB_MSG = POINTER(NET_EHOME_PREVIEW_CB_MSG)

PREVIEW_DATA_CB = fun_ctype(c_bool, C_LONG, POINTER(NET_EHOME_PREVIEW_CB_MSG), POINTER(c_void_p))


# 预览回调参数结构体
class NET_EHOME_PREVIEW_DATA_CB_PARAM(Structure):
    _fields_ = [
        ('fnPreviewDataCB', PREVIEW_DATA_CB),  # 数据回调函数
        ('pUserData', c_void_p),  # 用户参数, 在fnPreviewDataCB回调出来
        ('byStreamFormat', C_BYTE),  # 封装格式：0- PS
        ('byRes', C_BYTE * 127),  # 保留
    ]


class NET_EHOME_VOICETALK_DATA_CB_INFO(Structure):
    _fields_ = [
        ('pData', c_void_p),  # 数据指针
        ('dwDataLen', C_DWORD),  # 数据长度
        ('byRes', C_BYTE * 128),  # 保留
    ]


LPNET_EHOME_VOICETALK_DATA_CB_INFO = POINTER(NET_EHOME_VOICETALK_DATA_CB_INFO)

VOICETALK_DATA_CB = fun_ctype(c_bool, C_LONG, NET_EHOME_VOICETALK_DATA_CB_INFO, POINTER(c_void_p))


class NET_EHOME_VOICETALK_NEWLINK_CB_INFO(Structure):
    _fields_ = [
        ('szDeviceID', C_BYTE * 256),  # 设备标示符(出参)
        ('dwEncodeType', C_DWORD),
        # SDK赋值,当前对讲设备的语音编码类型,0- G722_1，1-G711U，2-G711A，3-G726，4-AAC，5-MP2L2，6-PCM, 7-MP3, 8-G723, 9-MP1L2, 10-ADPCM, 99-RAW(未识别类型)(出参)
        ('sDeviceSerial', C_BYTE),  # 设备序列号，数字序列号(出参)
        ('dwAudioChan', C_DWORD),  # 对讲通道(出参)
        ('lSessionID', C_DWORD),  # 设备分配给该回放会话的ID，0表示无效(出参)
        ('byToken', C_BYTE * 64),
        ('fnVoiceTalkDataCB', VOICETALK_DATA_CB),  # 数据回调函数(入参)
        ('pUserData', c_void_p),  # 用户参数, 在fnVoiceTalkDataCB回调出来(入参)
        ('byRes', C_BYTE * 48),  # 保留
    ]


VOICETALK_NEWLINK_CB = fun_ctype(c_bool, C_LONG, POINTER(NET_EHOME_VOICETALK_NEWLINK_CB_INFO), POINTER(c_void_p))


class NET_EHOME_LISTEN_VOICETALK_CFG(Structure):
    _fields_ = [
        ('struIPAdress', NET_EHOME_IPADDRESS),  # 本地监听信息，IP为0.0.0.0的情况下，默认为本地地址
        ('fnNewLinkCB', VOICETALK_NEWLINK_CB),  # 新连接回调函数
        ('pUser', c_void_p),  # 用户参数，在fnNewLinkCB中返回出来
        ('byLinkMode', C_BYTE),  # 0：TCP，1：UDP (UDP保留)
        ('byLinkEncrypt', C_BYTE),  # 是否启用链路加密,TCP通过TLS传输，UDP(包括NPQ)使用DTLS传输，0-不启用，1-启用
        ('byRes', C_BYTE * 126),  # 保留
    ]


# 语音连接回调函数
VOICETALK_NEWLINK_CB = fun_ctype(c_bool, C_LONG, POINTER(NET_EHOME_VOICETALK_NEWLINK_CB_INFO), POINTER(c_void_p))


class NET_EHOME_VOICETALK_DATA_CB_PARAM(Structure):
    _fields_ = [
        ('fnVoiceTalkDataCB', VOICETALK_DATA_CB),  # 数据回调函数
        ('pUserData', C_WORD),  # 用户参数, 在fnVoiceTalkDataCB回调出来
        ('byRes', C_BYTE * 128),
    ]


# 地址信息结构体
class NET_EHOME_IPADDRESS(Structure):
    _fields_ = [
        ('szIP', C_BYTE * 128),  # IP 地址。最大长度为 128 字节。
        ('wPort', C_WORD),  # 端口
        ('byRes', C_BYTE * 2),
    ]


class NET_EHOME_XML_REMOTE_CTRL_PARAM(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),  # 结构体大小
        ("lpInbuffer", c_void_p),  # 输入缓冲区指针
        ("dwInBufferSize", C_DWORD),  # 输入缓冲区大小
        ("dwSendTimeOut", C_DWORD),  # 发送超时时间
        ("dwRecvTimeOut", C_DWORD),  # 接收超时时间
        ("lpOutBuffer", c_void_p),  # 输出缓冲区指针
        ("dwOutBufferSize", C_DWORD),  # 输出缓冲区大小
        ("lpStatusBuffer", c_void_p),  # 状态缓冲区指针，若不需要可置为NULL
        ("dwStatusBufferSize", C_DWORD),  # 状态缓冲区大小
        ("byRes", C_BYTE * 16)  # 保留字段
    ]


class NET_EHOME_VOICE_TALK_IN(Structure):
    _fields_ = [
        ("dwVoiceChan", C_DWORD),  # 通道号
        ("struStreamSever", NET_EHOME_IPADDRESS),  # 流媒体地址
        ("byEncodingType", C_BYTE * 9),  # 语音对讲编码类型
        ("byLinkEncrypt", C_BYTE),  # 链接加密
        ("byBroadcast", C_BYTE),  # 语音广播标识, 设备接收到本标识为1后不进行音频采集发送给对端
        ("byBroadLevel", C_BYTE),  # 语音广播优先级标识, 0~15优先级从低到高, 当存在byBroadcast为1时, 0标识最低优先级。当存在byBroadcast为0时, 本节点无意义为保留字节
        ("byBroadVolume", C_BYTE),  # 语音广播音量, 0~15音量从低到高, 当存在byBroadcast为1时, 0标识最低音量。当存在byBroadcast为0时, 本节点无意义为保留字节
        ("byAudioSamplingRate", C_BYTE),  # 音频采样率 0-默认, 1-16kHZ, 2-32kHZ, 3-48kHZ, 4-44.1kHZ, 5-8kHZ
        ("byRes", C_BYTE * 114),  # 保留字节
    ]


class NET_EHOME_VOICE_TALK_OUT(Structure):
    _fields_ = [
        ("lSessionID", C_DWORD),  # 语音对讲请求的会话ID，由设备返回
        ("lHandle", C_DWORD),  # 输出参数句柄，在异步模式中作为异步回调的标识。对应 NET_EHOME_CMSCB_DATA 中的dwHandle。
        ("byRes", C_BYTE * 124),  # 保留，设为0。最大长度为124 字节。
    ]


class NET_EHOME_PUSHVOICE_IN(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("lSessionID", C_LONG),
        ("byToken", C_BYTE * 64),  # 保留，设为0。最大长度为64 字节。
        ("byRes", C_BYTE * 64),  # 保留，设为0。最大长度为64 字节。
    ]


class NET_EHOME_PUSHVOICE_OUT(Structure):
    _fields_ = [
        ("dwSize", C_DWORD),
        ("lHandle", C_LONG),
        ("byRes", C_BYTE * 124),  # 保留，设为0。最大长度为64 字节。
    ]


class NET_EHOME_VOICETALK_DATA(Structure):
    _fields_ = [
        ("pData", c_void_p),  # 数据指针
        ("dwDataLen", C_DWORD),  # 数据长度
        ("byRes", C_BYTE * 128),
    ]


# 回放数据结构体
class NET_EHOME_PLAYBACK_DATA_CB_INFO(Structure):
    _fields_ = [
        ('dwType', C_DWORD),  # 类型 1-头信息 2-码流数据 3-回放停止信令
        ('pData', c_void_p),  # 数据指针
        ('dwDataLen', C_DWORD),  # 数据长度
        ('byRes', C_BYTE * 128),
    ]


LPNET_EHOME_PLAYBACK_DATA_CB_INFO = POINTER(NET_EHOME_PLAYBACK_DATA_CB_INFO)

PLAYBACK_DATA_CB = fun_ctype(c_bool, C_LONG, POINTER(NET_EHOME_PLAYBACK_DATA_CB_INFO), POINTER(c_void_p))


# 预览请求参数结构体（适用于 64 位 Windows 或 Linux 操作系统）
class NET_EHOME_PLAYBACK_NEWLINK_CB_INFO(Structure):
    _fields_ = [
        ('szDeviceID', C_BYTE * 256),  # 设备标示符(出参)
        ('iSessionID', C_LONG),  # 设备分配给该取流会话的ID(出参)
        ('dwChannelNo', C_DWORD),  # 设备通道号(出参)
        ('sDeviceSerial', C_BYTE * 12),  # 设备序列号，数字序列号(出参)
        ('byStreamFormat', C_BYTE),  # 码流封装格式：0-PS 1-RTP(入参)
        ('byRes1', C_BYTE * 3),
        ('fnPlayBackDataCB', PLAYBACK_DATA_CB),  # 封装格式：0- PS,1-标准流(入参), 2-原始码流(即设备给什么流获取到的就是什么流)
        ('pUserData', c_void_p),
        ('byRes', C_BYTE * 112),
    ]


LPNET_EHOME_PLAYBACK_NEWLINK_CB_INFO = POINTER(NET_EHOME_PLAYBACK_NEWLINK_CB_INFO)

PLAYBACK_NEWLINK_CB = fun_ctype(c_bool, C_LONG, POINTER(NET_EHOME_PLAYBACK_NEWLINK_CB_INFO), POINTER(c_void_p))


# 按时间回放监听参数结构体
class NET_EHOME_PLAYBACK_LISTEN_PARAM(Structure):
    _fields_ = [
        ('struIPAdress', NET_EHOME_IPADDRESS),  # 本地监听信息，IP为0.0.0.0的情况下，默认为本地地址，多个网卡的情况下，默认为从操作系统获取到的第一个
        ('fnNewLinkCB', PLAYBACK_NEWLINK_CB),  # 回放请求回调函数，当收到预览连接请求后，SDK会回调该回调函数。
        ('pUser', c_void_p),  # 用户参数，在fnNewLinkCB中返回出来
        ('byLinkMode', C_BYTE),  # 0：TCP，1：UDP 2: HRUDP方式
        ('byRes', C_BYTE * 127),
    ]


# 回放回调参数结构体
class NET_EHOME_PLAYBACK_DATA_CB_PARAM(Structure):
    _fields_ = [
        ('fnPlayBackDataCB', PLAYBACK_DATA_CB),  # 数据回调函数
        ('pUserData', c_void_p),  # 用户参数, 在fnPreviewDataCB回调出来
        ('byStreamFormat', C_BYTE),  # 码流封装格式：0-PS 1-RTP
        ('byRes', C_BYTE * 127),  # 保留
    ]


class NET_EHOME_PLAYBACKBYNAME(Structure):
    _fields_ = [
        ('szFileName', C_BYTE * 100),  # 回放的文件名
        ('dwSeekType', C_DWORD),  # 0-按字节长度计算偏移量  1-按时间（秒数）计算偏移量
        ('dwFileOffset', C_DWORD),  # 文件偏移量，从哪个位置开始下载，如果dwSeekType为0，偏移则以字节计算，为1则以秒数计算
        ('dwFileSpan', C_DWORD),  # 下载的文件大小，为0时，表示下载直到该文件结束为止，如果dwSeekType为0，大小则以字节计算，为1则以秒数计算
    ]


class NET_EHOME_PLAYBACKBYTIME(Structure):
    _fields_ = [
        ('struStartTime', NET_EHOME_TIME),  # 按时间回放的开始时间
        ('struStopTime', NET_EHOME_TIME),  # 按时间回放的结束时间
        ('byLocalOrUTC', C_BYTE),  # 0-设备本地时间，即设备OSD时间  1-UTC时间
        ('byDuplicateSegment', C_BYTE),  # byLocalOrUTC为1时无效 0-重复时间段的前段 1-重复时间段后端
    ]


class NET_EHOME_PLAYBACKMODE(Union):
    _fields_ = [
        ("byLen", C_BYTE * 512),
        ("struPlayBackbyName", NET_EHOME_PLAYBACKBYNAME),
        ("struPlayBackbyTime", NET_EHOME_PLAYBACKBYTIME)
    ]


# 回放请求的输入参数结构体
class NET_EHOME_PLAYBACK_INFO_IN(Structure):
    _fields_ = [
        ('dwSize', C_DWORD),  #
        ('dwChannel', C_DWORD),  # 回放的通道号
        ('byPlayBackMode', C_BYTE),  # 回放下载模式 0－按名字 1－按时间
        ('byStreamPackage', C_BYTE),  # 回放码流类型，设备端发出的码流格式 0－PS（默认） 1－RTP
        ('byRes', C_BYTE * 2),  # 保留
        ('unionPlayBackMode', NET_EHOME_PLAYBACKMODE),  # 保留
        ('struStreamSever', NET_EHOME_IPADDRESS),  # 保留
    ]


class NET_EHOME_PLAYBACK_INFO_OUT(Structure):
    _fields_ = [
        ('lSessionID', C_DWORD),  # 目前协议不支持，返回-1
        ('lHandle', C_DWORD),  # 设置了回放异步回调之后，该值为消息句柄，回调中用于标识
        ('byRes', C_BYTE * 124),  # 保留
    ]


class NET_EHOME_PUSHPLAYBACK_IN(Structure):
    _fields_ = [
        ('dwSize', C_DWORD),
        ('lSessionID', C_DWORD),
        ('byKeyMD5', C_BYTE * 32),  # 码流加密秘钥,两次MD5
        ('byRes', C_BYTE * 96),  # 保留
    ]


class NET_EHOME_PUSHPLAYBACK_OUT(Structure):
    _fields_ = [
        ('dwSize', C_DWORD),
        ('lHandle', C_DWORD),
        ('byRes', C_BYTE * 124),  # 保留
    ]
