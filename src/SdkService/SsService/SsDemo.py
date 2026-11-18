# -*- coding: utf-8 -*-
# @Time : 2023/9/8 11:02
# @Author : qiu jiahang
import ctypes
import os
from ctypes import *
import platform

from src.Common import glo
from src.SdkService.CmsService.HCISUPCMS import NET_EHOME_IPADDRESS, load_library, libeay_dllpath, ssleay_dllpath, \
    target_dir
from src.SdkService.SsService.HCISUPSS import NET_EHOME_SS_CLIENT_PARAM, NET_EHOME_SS_LISTEN_PARAM, ss_sdkdllpath, \
    NET_EHOME_SS_INIT_CFG_TYPE, strPathSqlite
from src.SdkService.SsService.SSCallBack import pss_message_callback, pss_storage_callback, pss_ssrw_callback


class ssClass(object):

    def __init__(self):
        self.ssDLL = self.loadDLL()  # 初始化sdk
        self.ssHandle = -1  # 监听句柄
        self.client = -1
        glo.set_value('ssDLL', self.ssDLL)

    def loadDLL(self):
        '''
        根据操作系统加载sdk动态库
        :return:
        '''
        try:
            print("ss_sdkdllpath: ", ss_sdkdllpath)
            self.ssDLL = load_library(ss_sdkdllpath)
            libeay32_p = ctypes.cast(ctypes.c_char_p(libeay_dllpath.encode()), POINTER(c_void_p))
            ssleay32_p = ctypes.cast(ctypes.c_char_p(ssleay_dllpath.encode()), POINTER(c_void_p))
            self.ssDLL.NET_ESS_SetSDKInitCfg(
                NET_EHOME_SS_INIT_CFG_TYPE.NET_EHOME_SS_INIT_CFG_LIBEAY_PATH.value,
                libeay32_p)
            self.ssDLL.NET_ESS_SetSDKInitCfg(
                NET_EHOME_SS_INIT_CFG_TYPE.NET_EHOME_SS_INIT_CFG_SSLEAY_PATH.value,
                ssleay32_p)

            strPathSqlite_p = ctypes.cast(ctypes.c_char_p(strPathSqlite.encode()), POINTER(c_void_p))
            self.ssDLL.NET_ESS_SetSDKInitCfg(NET_EHOME_SS_INIT_CFG_TYPE.NET_EHOME_SS_INIT_CFG_SQLITE3_PATH.value,
                                             strPathSqlite_p)

            self.ssDLL.NET_ESS_Init()

            # 设置图片存储服务器公网地址 （当存在内外网映射时使用）
            pSSParam = NET_EHOME_IPADDRESS()
            ssAddress = ctypes.create_string_buffer(glo.get_value("PicServerIP").encode())
            ctypes.memmove(pSSParam.szIP, ssAddress, ctypes.sizeof(ssAddress))
            pSSParam.wPort = glo.get_value("PicServerPort")

            self.ssDLL.NET_ESS_SetSDKInitCfg(NET_EHOME_SS_INIT_CFG_TYPE.NET_EHOME_SS_INIT_CFG_PUBLIC_IP_PORT.value,
                                             ctypes.byref(pSSParam))

            self.ssDLL.NET_ESS_SetLogToFile(3, (target_dir + '/IsupSDKLog/').encode('utf-8'), False)  # 日志
            return self.ssDLL
        except OSError as e:
            print('cms 动态库加载失败', e)


    def startSsListen(self):
        """开启ss服务监听"""
        pSSListenParam = NET_EHOME_SS_LISTEN_PARAM()
        ssAddress = ctypes.create_string_buffer(glo.get_value("PicServerListenIP").encode())
        ctypes.memmove(pSSListenParam.struAddress.szIP, ssAddress, ctypes.sizeof(ssAddress))
        pSSListenParam.struAddress.wPort = glo.get_value("PicServerListenPort")

        strKMS_UserName = ctypes.create_string_buffer('test'.encode())
        ctypes.memmove(pSSListenParam.szKMS_UserName, strKMS_UserName, ctypes.sizeof(strKMS_UserName))
        strKMS_Password = ctypes.create_string_buffer('12345'.encode())
        ctypes.memmove(pSSListenParam.szKMS_Password, strKMS_Password, ctypes.sizeof(strKMS_Password))
        strAccessKey = ctypes.create_string_buffer('test'.encode())
        ctypes.memmove(pSSListenParam.szAccessKey, strAccessKey, ctypes.sizeof(strAccessKey))
        strSecretKey = ctypes.create_string_buffer('12345'.encode())
        ctypes.memmove(pSSListenParam.szSecretKey, strSecretKey, ctypes.sizeof(strSecretKey))
        pSSListenParam.byHttps = 0
        pSSListenParam.bySecurityMode = 1

        pSSListenParam.fnSSMsgCb = pss_message_callback
        pSSListenParam.fnSStorageCb = pss_storage_callback
        pSSListenParam.fnSSRWCb = pss_ssrw_callback

        self.ssHandle = self.ssDLL.NET_ESS_StartListen(ctypes.byref(pSSListenParam))
        if (self.ssHandle < 0):
            print('NET_ESS_StartListen Fail,err code: ', self.ssDLL.NET_ESS_GetLastError())
        else:
            print('存储服务器: ', glo.get_value("PicServerListenIP") + '_' + str(glo.get_value("PicServerListenPort")))

    def stopSsListen(self):
        """ss服务停止监听"""
        if (self.ssHandle > -1):
            self.ssDLL.NET_ESS_StopListen(self.ssHandle)
            self.ssDLL.NET_ESS_Fini()

    def ssCreateClient(self, file_path):
        """
        创建图片上传客户端
        file_path = "E:\SDK_Demo\ISUP\python\pythonProject\\file\image.jpg"
        """
        pClientParam = NET_EHOME_SS_CLIENT_PARAM()
        PicServerType = glo.get_value('PicServerType')
        if PicServerType == 1:
            pClientParam.enumType = 2
        elif PicServerType == 2:
            pClientParam.enumType = 4
        elif PicServerType == 3:
            pClientParam.enumType = 3
        else:
            print('存储服务器类型选择错误,请检查！')
            return False
        PicServerIP = glo.get_value('PicServerIP')
        PicServerPort = glo.get_value('PicServerPort')

        ip_address = create_string_buffer(PicServerIP.encode())

        ctypes.memmove(pClientParam.struAddress.szIP, ip_address, ctypes.sizeof(ip_address))
        pClientParam.struAddress.wPort = PicServerPort
        pClientParam.byHttps = 0
        client = self.ssDLL.NET_ESS_CreateClient(ctypes.byref(pClientParam))
        self.client = client
        if self.client < 0:
            error = self.ssDLL.NET_ESS_GetLastError()
            print(f"创建图片上传客户端失败，错误码:{error}")
            return False
        set_time = self.ssDLL.NET_ESS_ClientSetTimeout(self.client, 6000, 6000)
        if not set_time:
            error = self.ssDLL.NET_ESS_GetLastError()
            print(f"图片上传设置超时失败，错误码:{error}")

        bkms_username = self.ssDLL.NET_ESS_ClientSetParam(client, c_char_p("KMS-Username".encode()),
                                                          c_char_p("test".encode()))
        bkms_password = self.ssDLL.NET_ESS_ClientSetParam(client, c_char_p("KMS-Password".encode()),
                                                          c_char_p("12345".encode()))
        # print(bkms_username, bkms_password)
        bcloud_ak = self.ssDLL.NET_ESS_ClientSetParam(client, c_char_p("Access-Key".encode()),
                                                      c_char_p("test".encode()))
        bcloud_sk = self.ssDLL.NET_ESS_ClientSetParam(client, c_char_p("Secret-Key".encode()),
                                                      c_char_p("12345".encode()))

        bset_param = self.ssDLL.NET_ESS_ClientSetParam(client, c_char_p('File-Path'.encode()),
                                                       c_char_p(file_path.encode()))

    def ssUploadPic(self):
        """上传图片到存储服务，返回URL"""

        szUrl = ctypes.create_string_buffer(b'', 4096)
        ss = cast(szUrl, c_char_p)
        doUpload = self.ssDLL.NET_ESS_ClientDoUpload(self.client, ss, 4095)
        if (doUpload < 0):
            error = self.ssDLL.NET_ESS_GetLastError()
            print(f"文件上传失败，上传句柄：{doUpload}，错误码:{error}")
        else:
            url = "http://" + glo.get_value('PicServerIP') + ":" \
                  + str(glo.get_value('PicServerPort')) + ss.value.decode('UTF-8')
            print(f"NET_ESS_ClientDoUpload succeed,Pic Url: ：{url}")
            return url

    def ssDestroyClient(self):
        """销毁存储客户端"""

        if self.ssDLL.NET_ESS_DestroyClient(self.client):
            self.client = -1
            print('图片上传客户端销毁')
