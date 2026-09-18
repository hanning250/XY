# -*- coding: utf-8 -*-
# @Time : 2023/9/8 10:59
# @Author : qiu jiahang

from ctypes import Structure, c_void_p, CFUNCTYPE, c_bool, c_long, POINTER
from enum import Enum

from src.SdkService.CmsService.HCISUPCMS import NET_EHOME_IPADDRESS, C_DWORD, C_BYTE, target_dir, system_type, fun_ctype

ams_sdkdllpath_dict = {'windows64': target_dir + '\\lib\\' + 'HCISUPAlarm.dll',
                       'windows32': target_dir + '\\lib\\' + 'HCISUPAlarm.dll',
                       'linux64': target_dir + '/lib/libHCISUPAlarm.so',
                       'linux32': target_dir + '/lib/libHCISUPAlarm.so'}
ams_sdkdllpath = ams_sdkdllpath_dict[system_type]


# 枚举报警管理服务器的初始化配置类型。
class NET_EHOME_EALARM_INIT_CFG_TYPE(Enum):
    NET_EHOME_EALARM_INIT_CFG_LIBEAY_PATH = 0  # 设置OpenSSL的libeay32.dll/libcrypto.so所在路径
    NET_EHOME_EALARM_INIT_CFG_SSLEAY_PATH = 1  # 设置OpenSSL的ssleay32.dll/libssl.so所在路径


# 报警信息结构体
class NET_EHOME_ALARM_MSG(Structure):
    _fields_ = [
        ('dwAlarmType', C_DWORD),  # 报警类型，见EN_ALARM_TYPE
        ('pAlarmInfo', c_void_p),  # 报警内容（结构体）
        ('dwAlarmInfoLen', C_DWORD),  # 结构体报警内容长度
        ('pXmlBuf', c_void_p),  # 报警内容（XML）
        ('dwXmlBufLen', C_DWORD),  # xml报警内容长度
        ('sSerialNumber', C_BYTE * 12),  # 设备序列号，用于进行Token认证
        ('byRes', C_BYTE * 20)
    ]


LPNET_EHOME_ALARM_MSG = POINTER(NET_EHOME_ALARM_MSG)

EHomeMsgCallBack = fun_ctype(c_bool, c_long, POINTER(NET_EHOME_ALARM_MSG), POINTER(c_void_p))


# 报警监听参数结构体
class NET_EHOME_ALARM_LISTEN_PARAM(Structure):
    _fields_ = [
        ('struAddress', NET_EHOME_IPADDRESS),  # 本地监听信息，IP为0.0.0.0的情况下，默认为本地地址，多个网卡的情况下，默认为从操作系统获取到的第一个
        ('fnMsgCb', EHomeMsgCallBack),  # 报警信息回调函数
        ('pUserData', c_void_p),  # 用户数据
        ('byProtocolType', C_BYTE),  # 协议类型，0-TCP,1-UDP
        ('byUseCmsPort', C_BYTE),  # 是否复用CMS端口,0-不复用，非0-复用，如果复用cms端口，协议类型字段无效（此时本地监听信息struAddress填本地回环地址）
        ('byUseThreadPool', C_BYTE),  # 0-回调报警时，使用线程池，1-回调报警时，不使用线程池，默认情况下，报警回调的时候，使用线程池
        ('byRes', C_BYTE),
        ('dwKeepAliveSec', C_DWORD),  # 心跳间隔（单位：秒,0:默认为30S）
        ('dwTimeOutCount', C_DWORD),  # 心跳超时次数（0：默认为3）
        ('byRes', C_BYTE * 20),
    ]


# 关于通过 HTTP 上传报警信息的结构体。
class NET_EHOME_ALARM_ISAPI_INFO(Structure):
    _fields_ = [
        ('pAlarmData', c_void_p),  # 报警数据
        ('dwAlarmDataLen', C_DWORD),  # 报警数据长度
        ('byDataType', C_BYTE),  # 0-invalid,1-xml,2-json
        ('byPicturesNumber', C_BYTE),  # 图片数量
        ('byRes', C_BYTE * 2),  #
        ('pPicPackData', c_void_p),  # 图片变长部分,byPicturesNumber个NET_EHOME_ALARM_ISAPI_PICDATA
        ('byRes1', C_BYTE * 32)
    ]

LPNET_EHOME_ALARM_ISAPI_INFO = POINTER(NET_EHOME_ALARM_ISAPI_INFO)
