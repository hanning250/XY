# -*- coding: utf-8 -*-
# @Time : 2023/9/8 11:02
# @Author : qiu jiahang
from ctypes import Structure, c_uint32, c_byte, c_char_p, c_void_p, CFUNCTYPE, c_bool, POINTER, c_long
from enum import Enum

from src.SdkService.CmsService.HCISUPCMS import NET_EHOME_IPADDRESS, C_DWORD, C_BYTE, target_dir, system_type, fun_ctype

ss_sdkdllpath_dict = {'windows64': target_dir + '\\lib\\' + 'HCISUPSS.dll',
                      'windows32': target_dir + '\\lib\\' + 'HCISUPSS.dll',
                      'linux64': target_dir + '/lib/libHCISUPSS.so',
                      'linux32': target_dir + '/lib/libHCISUPSS.so'}
ss_sdkdllpath = ss_sdkdllpath_dict[system_type]

# 设置sqlite3库的路径
strPathSqlite_dict = {'windows64': target_dir + '\\lib\\' + 'sqlite3.dll',
                      'windows32': target_dir + '\\lib\\' + 'sqlite3.dll',
                      'linux64': target_dir + '/lib/libsqlite3.so',
                      'linux32': target_dir + '/lib/libsqlite3.so'}
strPathSqlite = strPathSqlite_dict[system_type]


PSS_CLIENT_FILE_PATH_PARAM_NAME = "File-Path"  # 图片文件路径
PSS_CLIENT_VRB_FILENAME_CODE = "Filename-Code"  # VRB协议的FilenameCode
PSS_CLIENT_KMS_USER_NAME = "KMS-Username"  # KMS图片服务器用户名
PSS_CLIENT_KMS_PASSWORD = "KMS-Password"  # KMS图片服务器密码
PSS_CLIENT_CLOUD_AK_NAME = "Access-Key"  # 云存储协议AcessKey
PSS_CLIENT_CLOUD_SK_NAME = "Secret-Key"  # 云存储协议SecretKey


# 枚举存储服务器的回调数据类型。
class NET_EHOME_SS_MSG_TYPE(Enum):
    NET_EHOME_SS_MSG_TOMCAT = 1  # Tomcat回调函数
    NET_EHOME_SS_MSG_KMS_USER_PWD = 2  # KMS用户名密码校验
    NET_EHOME_SS_MSG_CLOUD_AK = 3  # EHome5.0存储协议AK回调
    NET_EHOME_SS_MSG_ADDR = 4


# 枚举初始化配置类型。
class NET_EHOME_SS_INIT_CFG_TYPE(Enum):
    NET_EHOME_SS_INIT_CFG_SDK_PATH = 1  # 设置SS组件加载路径（仅Linux版本支持）
    NET_EHOME_SS_INIT_CFG_CLOUD_TIME_DIFF = 2  # 设置运存储的请求时间差值, 默认15分钟, 最小5分钟, 最大60分钟
    NET_EHOME_SS_INIT_CFG_PUBLIC_IP_PORT = 3  # 设置公网地址(当存在内外网映射时)
    NET_EHOME_SS_INIT_CFG_LIBEAY_PATH = 4  # 设置OpenSSL库libeay32.dll的路径
    NET_EHOME_SS_INIT_CFG_SSLEAY_PATH = 5  # 设置OpenSSL库ssleay32.dll的路径
    NET_EHOME_SS_INIT_CFG_SQLITE3_PATH = 6  # 设置sqlite3库的路径


# 文件上传客户端参数结构体
class NET_EHOME_SS_CLIENT_PARAM(Structure):
    _fields_ = [
        ('enumType', C_DWORD),  # 图片上传客户端类型  NET_EHOME_SS_CLIENT_TYPE
        ('struAddress', NET_EHOME_IPADDRESS),  # 图片服务器地址
        ('byHttps', C_BYTE),  # 是否启用HTTPs
        ('byRes', C_BYTE * 63),
    ]


# 读写扩展回调函数结构体
class NET_EHOME_SS_RW_PARAM(Structure):
    _fields_ = [
        ('pFileName', c_char_p),  # 文件名
        ('pFileBuf', c_void_p),  # 文件内容
        ('dwFileLen', POINTER(C_DWORD)),  # 文件大小
        ('pFileUrl', c_char_p),  # 文件url
        ('pUser', c_void_p),
        ('byAct', C_BYTE),  # 读写操作：0-写文件，1-读文件
        ('byUseRetIndex', C_BYTE),  # 是否使用上层返回的pRetIndex：0-不使用，1-使用
        ('byRes1', C_BYTE * 2),
        ('pRetIndex', c_char_p),  # 上层设置的索引，pRetIndex为0时，可不设置，pRetIndex为1时候，设置
        ('byRes', c_byte * 56),
    ]


# 云存储结构体
class NET_EHOME_SS_CLOUD_PARAM(Structure):
    _fields_ = [
        ('pPoolId', c_char_p),  # poolId 资源池id
        ('byPoolIdLength', C_BYTE),  # poolid 长度
        ('byRes1', C_BYTE * 3),  # poolid 长度
        ('dwErrorCode', C_DWORD),  # 云存储错误码
        ('byRes', C_BYTE * 500),
    ]


class NET_EHOME_SS_Union(Structure):
    _fields_ = [
        ('struCloud', NET_EHOME_SS_CLOUD_PARAM),
    ]


# 回调函数返回的扩展结构体
class NET_EHOME_SS_EX_PARAM(Structure):
    _fields_ = [
        ('byProtoType', C_BYTE),  # 存储协议类型 1-云存储，2-tomcat，3-kms，4-vrb, 5-中心存储协议
        ('byRes', C_BYTE * 23),
        ('unionStoreInfo', NET_EHOME_SS_Union),
    ]


EHomeSStorageCallBack = fun_ctype(c_bool, c_long, c_char_p, POINTER(c_void_p), c_uint32, POINTER(c_char_p),
                                  POINTER(c_void_p))
# 文件信息回调函数
EHomeSSMsgCallBack = fun_ctype(c_bool, c_long, c_byte, POINTER(c_void_p), c_uint32, POINTER(c_char_p), c_uint32,
                               POINTER(c_void_p))

EHomeSSRWCallBack = fun_ctype(c_bool, c_long, c_byte, c_char_p, POINTER(c_void_p), POINTER(c_long), c_char_p,
                              POINTER(c_void_p))
EHomeSSRWCallBackEx = fun_ctype(c_bool, c_long, NET_EHOME_SS_RW_PARAM, NET_EHOME_SS_EX_PARAM)


# 监听参数
class NET_EHOME_SS_LISTEN_PARAM(Structure):
    _fields_ = [
        ('struAddress', NET_EHOME_IPADDRESS),  # 本地监听信息，IP为0.0.0.0的情况下，默认为本地地址，多个网卡的情况下，默认为从操作系统获取到的第一个
        ('szKMS_UserName', C_BYTE * 512),  # KMS用户名
        ('szKMS_Password', C_BYTE * 512),  # KMS用户名
        ('fnSStorageCb', EHomeSStorageCallBack),  # 图片服务器信息存储回调函数
        ('fnSSMsgCb', EHomeSSMsgCallBack),  # 图片服务器信息Tomcat回调函数
        ('szAccessKey', C_BYTE * 64),  # EHome5.0存储协议AK
        ('szSecretKey', C_BYTE * 64),  # EHome5.0存储协议SK
        ('pUserData', c_void_p),  # 用户参数
        ('byHttps', C_BYTE),  # 是否启用HTTPs
        ('byRes1', C_BYTE * 3),
        ('fnSSRWCb', EHomeSSRWCallBack),  # 读写回调函数
        ('fnSSRWCbEx', EHomeSSRWCallBackEx),  # 读写回调函数扩展
        ('bySecurityMode', C_BYTE),
        ('byRes', C_BYTE * 51),
    ]
