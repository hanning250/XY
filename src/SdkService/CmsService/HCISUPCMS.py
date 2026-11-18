# -*- coding: utf-8 -*-
# @Time : 2023/9/8 11:01
# @Author : qiu jiahang

# 常量定义

import os
import platform
import re
from ctypes import *
from enum import Enum


def system_get_platform_info():
    sys_platform = platform.system().lower().strip()
    python_bit = platform.architecture()[0]
    python_bit_num = re.findall('(\d+)\w*', python_bit)[0]
    return sys_platform, python_bit_num


sys_platform, python_bit_num = system_get_platform_info()
system_type = sys_platform + python_bit_num
fun_ctype = None
if sys_platform == 'linux':
    load_library = cdll.LoadLibrary
    fun_ctype = CFUNCTYPE
elif sys_platform == 'windows':
    load_library = windll.LoadLibrary
    fun_ctype = WINFUNCTYPE
else:
    print("************不支持的平台**************")
    exit(0)
# 获取当前脚本文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

target_dir = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))

cms_sdkdllpath_dict = {'windows64': target_dir + '\\lib\\' + 'HCISUPCMS.dll',
                       'windows32': target_dir + '\\lib\\' + 'HCISUPCMS.dll',
                       'linux64': target_dir + '/lib/libHCISUPCMS.so',
                       'linux32': target_dir + '/lib/libHCISUPCMS.so'}
cms_sdkdllpath = cms_sdkdllpath_dict[system_type]

libeay_dllpath_dict = {'windows64': target_dir + '\\lib\\' + 'libeay32.dll',
                       'windows32': target_dir + '\\lib\\' + 'libeay32.dll',
                       'linux64': target_dir + '/lib/libcrypto.so',
                       'linux32': target_dir + '/lib/libcrypto.so'}
libeay_dllpath = libeay_dllpath_dict[system_type]

ssleay_dllpath_dict = {'windows64': target_dir + '\\lib\\' + 'ssleay32.dll',
                       'windows32': target_dir + '\\lib\\' + 'ssleay32.dll',
                       'linux64': target_dir + '/lib/libssl.so',
                       'linux32': target_dir + '/lib/libssl.so'}
ssleay_dllpath = ssleay_dllpath_dict[system_type]

strPathCom_dllpath_dict = {'windows64': target_dir + '\\lib\\' + 'HCAapSDKCom',
                           'windows32': target_dir + '\\lib\\' + 'HCAapSDKCom',
                           'linux64': target_dir + '/lib/HCAapSDKCom',
                           'linux32': target_dir + '/lib/HCAapSDKCom'}
strPathCom_dllpath = strPathCom_dllpath_dict[system_type]

C_LLONG_DICT = {'windows64': c_longlong, 'windows32': c_long, 'linux32': c_long, 'linux64': c_long}
C_LONG_DICT = {'windows64': c_long, 'windows32': c_long, 'linux32': c_int, 'linux64': c_int}
C_LDWORD_DICT = {'windows64': c_longlong, 'windows32': c_ulong, 'linux32': c_long, 'linux64': c_long}
C_DWORD_DICT = {'windows64': c_ulong, 'windows32': c_ulong, 'linux32': c_uint, 'linux64': c_uint}
C_HWND_DICT = {'windows64': c_void_p, 'windows32': c_void_p, 'linux32': c_uint, 'linux64': c_uint}

C_LLONG = C_LLONG_DICT[system_type]
C_LONG = C_LONG_DICT[system_type]
C_LDWORD = C_LDWORD_DICT[system_type]
C_DWORD = C_DWORD_DICT[system_type]
# C_BOOL = c_int
# C_UINT = c_uint
# C_BYTE = c_ubyte
# C_ENUM = c_int

C_HWND = C_HWND_DICT[system_type]
C_WORD = c_ushort
C_USHORT = c_ushort
C_SHORT = c_short
# C_LONG = c_int
C_BYTE = c_ubyte
C_UINT = c_uint
C_LPVOID = c_void_p
C_HANDLE = c_void_p
C_LPDWORD = POINTER(c_uint)
C_UINT64 = c_ulonglong
C_INT64 = c_longlong
C_BOOL = c_int

NET_SDK_MAX_FILE_PATH = 256
MAX_NAMELEN = 16  # DVR本地登陆名
MAX_RIGHT = 32  # 设备支持的权限（1-12表示本地权限，13-32表示远程权限）
NAME_LEN = 32  # 用户名长度
PASSWD_LEN = 16  # 密码长度
MAX_MASTER_KEY_LEN = 16
MAX_DEVICE_ID_LEN = 256  # 设备ID长度
MAX_DEVNAME_LEN = 32  # 设备名最大长度
MAX_DEVNAME_LEN_EX = 64  # 设备名最大长度
MAX_FULL_SERIAL_NUM_LEN = 64  # 最大完整序列号长度
NET_EHOME_SERIAL_LEN = 12  # 序列号长度
MAX_ANALOG_CHANNUM = 32
MAX_DIGIT_CHANNUM = 480
MAX_ANALOG_ALARMOUT = 32

ENUM_SEARCH_TYPE_ERR = -1
ENUM_SEARCH_RECORD_FILE = 0
ENUM_SEARCH_PICTURE_FILE = 1
ENUM_SEARCH_FLOW_INFO = 2
ENUM_SEARCH_DEV_LOG = 3
ENUM_SEARCH_ALARM_HOST_LOG = 4

'''
枚举定义
'''


# 枚举注册回调类型。
class EHOME_REGISTER_TYPE(Enum):
    ENUM_DEV_ON = 0  # 设备上线回调
    ENUM_DEV_OFF = 1  # 设备下线回调
    ENUM_DEV_ADDRESS_CHANGED = 2  # 设备地址发生变化
    ENUM_DEV_AUTH = 3  # Ehome5.0 设备认证回调
    ENUM_DEV_SESSIONKEY = 4  # Ehome5.0 设备Sessionkey回调
    ENUM_DEV_DAS_REQ = 5  # Ehome5.0 设备重定向请求回调
    ENUM_DEV_SESSIONKEY_REQ = 6  # EHome5.0设备sessionkey请求回调
    ENUM_DEV_DAS_REREGISTER = 7  # 设备重注册回调
    ENUM_DEV_DAS_PINGREO = 8  # 设备注册心跳
    ENUM_DEV_DAS_EHOMEKEY_ERROR = 9  # 校验密码失败
    ENUM_DEV_SESSIONKEY_ERROR = 10  # Sessionkey交互异常
    ENUM_DEV_SLEEP = 11  # 设备进入休眠状态（注：休眠状态下，设备无法做预览、回放、语音对讲、配置等CMS中的信令作响应；设备可通过NET_ECMS_WakeUp接口进行唤醒）


# 枚举初始化配置类型。
class NET_EHOME_CMS_INIT_CFG_TYPE(Enum):
    NET_EHOME_CMS_INIT_CFG_LIBEAY_PATH = 0  # 设置OpenSSL的libeay32.dll/libcrypto.so所在路径
    NET_EHOME_CMS_INIT_CFG_SSLEAY_PATH = 1  # 设置OpenSSL的ssleay32.dll/libssl.so所在路径


# 枚举本地配置类型。
class NET_EHOME_LOCAL_CFG_TYPE(Enum):
    UNDEFINE = -1  # 暂时没有具体的定义
    ACTIVE_ACCESS_SECURITY = 0  # 设备主动接入的安全性
    AMS_ADDRESS = 1  # 报警服务器本地回环地址
    SEND_PARAM = 2  # 发送参数配置
    SET_REREGISTER_MODE = 3  # 设置设备重复注册模式
    LOCAL_CFG_TYPE_GENERAL = 4  # 通用参数配置
    COM_PATH = 5  # COM路径
    SESSIONKEY_REQ_MOD = 6  # sessionkey请求是否回调，lpInBuff类型为HPR_BOOL *, HPR_TRUE / HPR_FALSE：回调 / 不回调
    DEV_DAS_PINGREO_CALLBACK = 7  # 设备心跳注册回调
    REGISTER_LISTEN_MODE = 8  # 注册监听模式,对应结构体为NET_EHOME_REGISTER_LISTEN_MODE
    STREAM_PLAYBACK_PARAM = 9  # 回放本地参数配置


# 地址信息结构体
class NET_EHOME_IPADDRESS(Structure):
    _fields_ = [
        ('szIP', C_BYTE * 128),  # IP 地址。最大长度为 128 字节。
        ('wPort', C_WORD),  # 端口
        ('byRes', C_BYTE * 2),
    ]


# 注册回调函数
DEVICE_REGISTER_CB = fun_ctype(c_bool, c_int16, c_uint32, POINTER(c_void_p), c_uint32, POINTER(c_void_p), c_uint32,
                               POINTER(c_void_p))


# 中心管理服务器监听参数结构体
class NET_EHOME_CMS_LISTEN_PARAM(Structure):
    _fields_ = [
        ('struAddress', NET_EHOME_IPADDRESS),  # 本地监听信息，IP为0.0.0.0的情况下，默认为本地地址，多个网卡的情况下，默认为从操作系统获取到的第一个
        ('fnCB', DEVICE_REGISTER_CB),  # 报警信息回调函数
        ('pUserData', c_void_p),  # 用户数据
        ('dwKeepAliveSec', C_DWORD),  # 心跳间隔（单位：秒），0：默认30秒
        ('dwTimeOutCount', C_DWORD),  # 心跳超时次数（0：默认3次）
        ('byRes', C_BYTE * 24)  # 保留，设为0
    ]


# 设备注册信息结构体
class NET_EHOME_DEV_REG_INFO(Structure):
    _fields_ = [
        ('dwSize', C_DWORD),  # 结构体大小
        ('dwNetUnitType', C_DWORD),  # 保留
        ('byDeviceID', C_BYTE * 256),  # 设备ID，最大长度256
        ('byFirmwareVersion', C_BYTE * 24),  # 固件版本信息
        ('struDevAdd', NET_EHOME_IPADDRESS),  # 设备地址
        ('dwDevType', C_DWORD),  # 设备类型
        ('dwManufacture', C_DWORD),  # 制造商代码
        ('byPassWord', C_BYTE * 32),  # 设备登录中心管理服务器的密码，用户根据需求进行验证
        ('sDeviceSerial', C_BYTE * 12),  # 设备序列号
        ('byReliableTransmission', C_BYTE),  # 可靠传输
        ('byWebSocketTransmission', C_BYTE),  # 网络接口传输
        ('bySupportRedirect', C_BYTE),  # 设备支持重定向注册 0-不支持 1-支持
        ('byDevProtocolVersion', C_BYTE * 6),  # 设备协议版本
        ('bySessionKey', C_BYTE * 16),  # Ehome5.0设备SessionKey
        ('byMarketType', C_BYTE),  # 0-无效（未知类型）,1-经销型，2-行业型
        ('bySupport', C_BYTE),  # 设备支持的功能情况，支持"与"操作。从右到左，
        # 第一位为1表示支持NPQ预览(0b00000001)
        # 第二位为1表示支持NPQ回放(0b00000010)
        # 第三位为1表示支持预览、回放和语音对讲链路加密传输(0b00000100)
        # 第四位为1表示支持HLS回放(0b00001000)
        # 第五位为1表示支持语音对讲链路纯广播传输—即只有下行数据无上行数据(0b00010000)
        ('byRes', C_BYTE * 25)
    ]


# 设备注册信息结构体（V12）
class NET_EHOME_DEV_REG_INFO_V12(Structure):
    _fields_ = [
        ('struRegInfo', NET_EHOME_DEV_REG_INFO),  # 注册信息
        ('struRegAddr', NET_EHOME_IPADDRESS),  # 设备注册的服务器地址
        ('sDevName', C_BYTE * 64),  # 设备名称
        ('byDeviceFullSerial', C_BYTE * 64),  # 设备完整序列号，设备型号+日期+短序号+扩展
        ('byRes', C_BYTE * 128)
    ]


LPNET_EHOME_DEV_REG_INFO_V12 = POINTER(NET_EHOME_DEV_REG_INFO_V12)


# Ehome5.0协议设备EhomeKey信息
class NET_EHOME_DEV_SESSIONKEY(Structure):
    _fields_ = [
        ('sDeviceID', C_BYTE * MAX_DEVICE_ID_LEN),  # 设备ID/*256*/
        ('sSessionKey', C_BYTE * MAX_MASTER_KEY_LEN)  # 设备Sessionkey/*16*/
    ]


# 黑名单管理服务器参数结构体
class NET_EHOME_BLACKLIST_SEVER(Structure):
    _fields_ = [
        ('struAdd', NET_EHOME_IPADDRESS),  # 服务器地址
        ('byServerName', C_BYTE * 32),  # 服务器名称
        ('byUserName', C_BYTE * 32),  # 用户名
        ('byPassWord', C_BYTE * 32),  # 密码
        ('byRes', C_BYTE * 64)
    ]


# 服务器信息结构体（V50）
class NET_EHOME_SERVER_INFO_V50(Structure):
    _fields_ = [
        ('dwSize', C_DWORD),
        ('dwKeepAliveSec', C_DWORD),  # 心跳间隔（单位：秒,0:默认为15S）
        ('dwTimeOutCount', C_DWORD),  # 心跳超时次数（0：默认为6）
        ('struTCPAlarmSever', NET_EHOME_IPADDRESS),  # 报警服务器地址（TCP协议）
        ('struUDPAlarmSever', NET_EHOME_IPADDRESS),  # 报警服务器地址（UDP协议）
        ('dwAlarmServerType', C_DWORD),  # 报警服务器类型0-只支持UDP协议上报，1-支持UDP、TCP两种协议上报
        ('struNTPSever', NET_EHOME_IPADDRESS),  # NTP服务器地址
        ('dwNTPInterval', C_DWORD),  # NTP校时间隔（单位：秒）
        ('struPictureSever', NET_EHOME_IPADDRESS),  # 图片服务器地址
        ('dwPicServerType', C_DWORD),  # 图片服务器类型图片服务器类型，1-VRB图片服务器，0-Tomcat图片服务,2-云存储3,3-KMS
        ('struBlackListServer', NET_EHOME_BLACKLIST_SEVER),  # 黑名单服务器
        ('struRedirectSever', NET_EHOME_IPADDRESS),  # Redirect Server
        ('byClouldAccessKey', C_BYTE * 64),  # 云存储AK
        ('byClouldSecretKey', C_BYTE * 64),  # 云存储SK
        ('byClouldHttps', C_BYTE),  # 云存储HTTPS使能 1-HTTPS 0-HTTP
        ('byRes1', C_BYTE * 3),
        ('dwAlarmKeepAliveSec', C_DWORD),  # 报警心跳间隔（单位：秒,0:默认为30s）
        ('dwAlarmTimeOutCount', C_DWORD),  # 报警心跳超时次数（0：默认为3）
        ('dwClouldPoolId', C_DWORD),  # 云存储PoolId
        ('byRes', C_BYTE * 368)
    ]


# 传输参数结构体
class NET_EHOME_PTXML_PARAM(Structure):
    _fields_ = [
        ('pRequestUrl', c_void_p),  # 请求URL
        ('dwRequestUrlLen', C_DWORD),  # 请求URL长度
        ('pCondBuffer', c_void_p),  # 条件缓冲区（XML格式数据）
        ('dwCondSize', C_DWORD),  # 条件缓冲区大小
        ('pInBuffer', c_void_p),  # 输入缓冲区（XML格式数据）
        ('dwInSize', C_DWORD),  # 输入缓冲区大小
        ('pOutBuffer', c_void_p),  # 输出缓冲区（XML格式数据）
        ('dwOutSize', C_DWORD),  # 输出缓冲区大小
        ('dwReturnedXMLLen', C_DWORD),  # 实际从设备接收到的XML数据的长度
        ('dwRecvTimeOut', C_DWORD),  # 默认5000ms
        ('dwHandle', C_DWORD),  # （输出参数）设置了回放异步回调之后，该值为消息句柄，回调中用于标识（新增）
        ('byRes', C_BYTE * 24)  # 保留
    ]


LPNET_EHOME_PTXML_PARAM = POINTER(NET_EHOME_PTXML_PARAM)


class NET_EHOME_XML_REMOTE_CTRL_PARAM(Structure):
    _fields_ = [
        ("dwSize", c_uint32),  # 结构体大小
        ("lpInbuffer", c_void_p),  # 输入缓冲区指针
        ("dwInBufferSize", c_uint32),  # 输入缓冲区大小
        ("dwSendTimeOut", c_uint32),  # 发送超时时间
        ("dwRecvTimeOut", c_uint32),  # 接收超时时间
        ("lpOutBuffer", c_void_p),  # 输出缓冲区指针
        ("dwOutBufferSize", c_uint32),  # 输出缓冲区大小
        ("lpStatusBuffer", c_void_p),  # 状态缓冲区指针，若不需要可置为NULL
        ("dwStatusBufferSize", c_uint32),  # 状态缓冲区大小
        ("byRes", c_byte * 16)  # 保留字段
    ]


# 预览请求
class NET_EHOME_PREVIEWINFO_IN(Structure):
    _fields_ = [
        ('iChannel', C_DWORD),  # 通道号
        ('dwStreamType', C_DWORD),  # 码流类型，0-主码流，1-子码流, 2-第三码流
        ('dwLinkMode', C_DWORD),  # 0：TCP方式,1：UDP方式,2: HRUDP方式
        ('struStreamSever', NET_EHOME_IPADDRESS),  # 流媒体地址
    ]


# 预览请求的输出参数结构体
class NET_EHOME_PREVIEWINFO_OUT(Structure):
    _fields_ = [
        ('lSessionID', C_DWORD),  # 会话ID
        ('byRes', C_BYTE * 128),
    ]


# 实时流传输请求的输入参数结构体
class NET_EHOME_PUSHSTREAM_IN(Structure):
    _fields_ = [
        ('dwSize', C_DWORD),  # 结构体大小
        ('lSessionID', C_DWORD),  # 会话ID
        ('byRes', C_BYTE * 128),
    ]


# 实时流传输请求的输出参数结构体
class NET_EHOME_PUSHSTREAM_OUT(Structure):
    _fields_ = [
        ('dwSize', C_DWORD),  # 结构体大小
        ('byRes', C_BYTE * 128),
    ]


# 时间参数
class NET_EHOME_TIME(Structure):
    _fields_ = [
        ('wYear', C_WORD),  # 年
        ('byMonth', C_BYTE),  # 月
        ('byDay', C_BYTE),  # 日
        ('byHour', C_BYTE),  # 时
        ('byMinute', C_BYTE),  # 分
        ('bySecond', C_BYTE),  # 秒
        ('byRes1', C_BYTE),
        ('wMSecond', C_WORD),  # 毫秒
        ('byRes', C_BYTE * 2),
    ]


# 视频文件查找条件结构体
class NET_EHOME_REC_FILE_COND(Structure):
    _fields_ = [
        ('dwChannel', C_DWORD),  # 通道号，从1开始
        ('dwRecType', C_DWORD),  # 0xff-全部类型录像（不包含图片类型）
        # 0-定时录像
        # 1-移动报警
        # 2-报警触发
        # 3-报警|动测
        # 4-报警&动测
        # 5-命令触发
        # 6-手动录像
        # 7-震动报警
        # 8-环境报警
        # 9-智能报警（或者取证录像）
        # 10（0x0a）-PIR报警
        # 11（0x0b）-无线报警
        # 12（0x0c）-呼救报警
        # 13（0x0d）全部报警
        # 100-全部类型图片
        # 101-车牌识别图片
        # 102-稽查报警图片
        # 103-手动抓拍图片
        # 104-回放抓拍图片
        ('struStartTime', NET_EHOME_TIME),  # 开始时间
        ('struStopTime', NET_EHOME_TIME),  # 结束时间
        ('dwStartIndex', C_DWORD),  # 查询起始位置
        ('dwMaxFileCountPer', C_DWORD),  # 单次搜索最大文件个数，最大文件个数，需要确定实际网络环境，建议最大个数为8
        ('byLocalOrUTC', C_BYTE),
        # 0-struStartTime和struStopTime中，表示的是设备本地时间，即设备OSD时间  1-struStartTime和struStopTime中，表示的是UTC时间
        ('byRes', C_BYTE * 63),
    ]


# 录像文件信息
class NET_EHOME_REC_FILE(Structure):
    _fields_ = [
        ('dwSize', C_DWORD),
        ('sFileName', c_char * 100),  # 文件名
        ('struStartTime', NET_EHOME_TIME),  # 文件的开始时间
        ('struStopTime', NET_EHOME_TIME),  # 文件的结束时间
        ('dwFileSize', C_DWORD),  # 文件的大小
        ('dwFileMainType', C_DWORD),  # 录像文件主类型
        ('dwFileSubType', C_DWORD),  # 录像文件子类型
        ('dwFileIndex', C_DWORD),  # 录像文件索引
        ('byTimeDiffH', C_BYTE),  # struStartTime、struStopTime与国际标准时间（UTC）的时差（小时），-12 ... +14,0xff表示无效
        ('byTimeDiffM', C_BYTE),  # struStartTime、struStopTime与国际标准时间（UTC）的时差（分钟），-30,0, 30, 45, 0xff表示无效
        ('byRes', C_BYTE * 126),
    ]
