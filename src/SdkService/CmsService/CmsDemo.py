# -*- coding: utf-8 -*-
# @Time : 2023/9/8 11:01
# @Author : qiu jiahang
import ctypes
import json
from ctypes import *

from src.Common import glo
from src.Common.ListenHelper import bind_ip_address
from src.Common.SdkInit import configure_com_path, configure_openssl, configure_sdk_log
from src.SdkService.CmsService.HCISUPCMS import *


@fun_ctype(c_bool, c_int16, c_uint32, POINTER(c_void_p), c_uint32, POINTER(c_void_p), c_uint32, POINTER(c_void_p))
def deviceRegisterCB(lUserID, dwDataType, pOutBuffer, dwOutLen, pInBuffer, dwInLen, pUser):
    try:
        print('dwDataType: ', dwDataType)
        if dwDataType == 3:
            # 登录秘钥验证
            pDevInfo = NET_EHOME_DEV_REG_INFO_V12()
            ctypes.memmove(ctypes.pointer(pDevInfo), pOutBuffer, ctypes.sizeof(pDevInfo))
            strDeviceID = str(pDevInfo.struRegInfo.byDeviceID, encoding="utf-8").rstrip('\x00')
            print(f"设备id :{strDeviceID}")
            # pInBuffer 赋值 ehomeKey
            str1 = glo.get_value('ISUPKey')
            b = ctypes.create_string_buffer(str1.encode())
            ctypes.memmove(pInBuffer, b, ctypes.sizeof(b))
            return True
        if dwDataType == 4:
            # sessionKey参数配置
            pDevInfo = NET_EHOME_DEV_REG_INFO_V12()
            ctypes.memmove(ctypes.pointer(pDevInfo), pOutBuffer, ctypes.sizeof(pDevInfo))
            pDevInfo = ctypes.cast(pOutBuffer, LPNET_EHOME_DEV_REG_INFO_V12).contents

            struSessionKey = NET_EHOME_DEV_SESSIONKEY()
            # print('byDeviceID:', ctypes.string_at(pDevInfo.struRegInfo.byDeviceID))
            # print('bySessionKey:', ctypes.string_at(pDevInfo.struRegInfo.bySessionKey))
            byDeviceID = str(pDevInfo.struRegInfo.byDeviceID, encoding="utf-8").rstrip('\x00')
            bySessionKey = str(pDevInfo.struRegInfo.bySessionKey, encoding="utf-8").rstrip('\x00')
            print('byDeviceID:', byDeviceID)
            # print('bySessionKey:', bySessionKey)
            # str(pDevInfo.struRegInfo.byDeviceID, encoding="utf-8").rstrip('\x00')
            ctypes.memmove(struSessionKey.sDeviceID, pDevInfo.struRegInfo.byDeviceID,
                           ctypes.sizeof(pDevInfo.struRegInfo.byDeviceID))
            ctypes.memmove(struSessionKey.sSessionKey, pDevInfo.struRegInfo.bySessionKey,
                           ctypes.sizeof(pDevInfo.struRegInfo.bySessionKey))
            if glo.get_value("cmsDLL").NET_ECMS_SetDeviceSessionKey(ctypes.byref(struSessionKey)) is False:
                print('NET_ECMS_GetLastError', glo.get_value("cmsDLL").NET_ECMS_GetLastError())

            if glo.get_value("amsDLL").NET_EALARM_SetDeviceSessionKey(ctypes.byref(struSessionKey)) is False:
                print('NET_EALARM_GetLastError', glo.get_value("amsDLL").NET_EALARM_GetLastError())
            return True
        if dwDataType == 5:
            b = {"Type": "DAS",
                 "DasInfo": {"Address": glo.get_value("DasServerIP"),
                             "Domain": "test.ys7.com",
                             "ServerID": "das_" + glo.get_value("DasServerIP") + "_" + str(
                                 glo.get_value("DasServerPort")),
                             "Port": int(glo.get_value("DasServerPort")),
                             "UdpPort": int(glo.get_value("DasServerPort"))
                             }}
            desinfo = json.dumps(b)
            b = ctypes.create_string_buffer(desinfo.encode())
            ctypes.memmove(pInBuffer, b, ctypes.sizeof(b))
            return True
        if dwDataType == 0:
            # 设备成功上线
            strAmsIP = glo.get_value("AlarmServerIP")
            strSSIP = glo.get_value("PicServerIP")
            ams_address = ctypes.create_string_buffer(strAmsIP.encode())
            ss_address = ctypes.create_string_buffer(strSSIP.encode())
            byClouldAccessKey = ctypes.create_string_buffer('test'.encode())
            byClouldSecretKey = ctypes.create_string_buffer('12345'.encode())
            pDevInfo = NET_EHOME_DEV_REG_INFO_V12()
            ctypes.memmove(pointer(pDevInfo), pOutBuffer, sizeof(pDevInfo))
            strEhomeServerInfo = NET_EHOME_SERVER_INFO_V50()

            # 设置报警服务器地址、端口、类型
            memmove(strEhomeServerInfo.struUDPAlarmSever.szIP, ams_address, sizeof(ams_address))
            memmove(strEhomeServerInfo.struTCPAlarmSever.szIP, ams_address, sizeof(ams_address))
            strEhomeServerInfo.dwAlarmServerType = glo.get_value("AlarmServerType")
            strEhomeServerInfo.struTCPAlarmSever.wPort = glo.get_value("AlarmServerTCPPort")
            strEhomeServerInfo.struUDPAlarmSever.wPort = glo.get_value("AlarmServerUDPPort")
            memmove(strEhomeServerInfo.byClouldAccessKey, byClouldAccessKey, sizeof(byClouldAccessKey))
            memmove(strEhomeServerInfo.byClouldSecretKey, byClouldSecretKey, sizeof(byClouldSecretKey))

            # 设置图片存储服务器地址、端口、类型
            memmove(strEhomeServerInfo.struPictureSever.szIP, ss_address, sizeof(ss_address))
            strEhomeServerInfo.struPictureSever.wPort = glo.get_value("PicServerPort")
            strEhomeServerInfo.dwPicServerType = glo.get_value("PicServerType")
            info_size = sizeof(strEhomeServerInfo)
            memmove(pInBuffer, pointer(strEhomeServerInfo), info_size)
            strDeviceID = str(pDevInfo.struRegInfo.byDeviceID, encoding="utf-8").rstrip('\x00')
            glo.register_device(strDeviceID, lUserID)
            print(f"设备上线成功 设备ID：{strDeviceID}  登录句柄iUserID：{lUserID}")
            return True
        if dwDataType == 1:
            # 设备离线
            device_id = glo.get_value('userDeviceMap', {}).get(lUserID)
            glo.unregister_device(lUserID)
            print(f"设备离线 设备ID：{device_id}  登录句柄iUserID：{lUserID}")
            return True
    except Exception as e:
        print('error', e)


class cmsClass(object):
    '''注册服务模块功能'''

    @staticmethod
    def _cms_user_id(user_id=None):
        if user_id is None:
            return glo.resolve_cms_user_id()
        return user_id

    def __init__(self):  # __init__() 是类的初始化方法；它在类的实例化操作后会自动调用，不需要手动调用；
        self.cmsDLL = self.loadDLL()  # 初始化sdk
        self.cmsHandle = -1  # 监听句柄
        self.fRegisterCallBack = None  # 注册回调函数实现
        self.struCMSListenPara = NET_EHOME_CMS_LISTEN_PARAM()  # 注册回调函数实现
        glo.set_value('cmsDLL', self.cmsDLL)

    def loadDLL(self):
        '''
        根据操作系统加载sdk动态库
        :return:
        '''
        try:
            print("cms_sdkdllpath: -----", cms_sdkdllpath)
            self.cmsDLL = load_library(cms_sdkdllpath)
            configure_openssl(
                self.cmsDLL,
                self.cmsDLL.NET_ECMS_SetSDKInitCfg,
                NET_EHOME_CMS_INIT_CFG_TYPE.NET_EHOME_CMS_INIT_CFG_LIBEAY_PATH.value,
                NET_EHOME_CMS_INIT_CFG_TYPE.NET_EHOME_CMS_INIT_CFG_SSLEAY_PATH.value,
            )
            self.cmsDLL.NET_ECMS_Init()
            configure_com_path(self.cmsDLL, self.cmsDLL.NET_ECMS_SetSDKLocalCfg, NET_EHOME_LOCAL_CFG_TYPE.COM_PATH.value)
            configure_sdk_log(self.cmsDLL, self.cmsDLL.NET_ECMS_SetLogToFile)
            return self.cmsDLL
        except OSError as e:
            print('cms 动态库加载失败', e)

    def startCmsListen(self):
        if self.fRegisterCallBack is None:
            self.fRegisterCallBack = deviceRegisterCB
        bind_ip_address(self.struCMSListenPara.struAddress, "CmsServerIP", "CmsServerPort")
        self.struCMSListenPara.fnCB = self.fRegisterCallBack
        self.cmsHandle = self.cmsDLL.NET_ECMS_StartListen(ctypes.byref(self.struCMSListenPara))
        if self.cmsHandle < 0:
            print('NET_ECMS_StartListen failed, error code: ', self.cmsDLL.NET_ECMS_GetLastError())
        else:
            # print(type(self.struCMSListenPara.struAddress.szIP))
            print('注册服务器: ', str(self.struCMSListenPara.struAddress.szIP, encoding="utf-8").rstrip('\x00') + '_' +
                  str(self.struCMSListenPara.struAddress.wPort))

    def stopCmsListen(self):
        if (self.cmsHandle > -1):
            self.cmsDLL.NET_ECMS_StopListen(self.cmsHandle)
            self.cmsDLL.NET_ECMS_Fini()

    # 透传接口
    def CMS_ISAPIPassThrough(self, url, transInput):
        m_struParam = NET_EHOME_PTXML_PARAM()
        print('url:', url)
        url = ctypes.create_string_buffer(bytes(url, encoding='utf-8'))
        m_struParam.pRequestUrl = ctypes.addressof(url)
        m_struParam.dwRequestUrlLen = len(url)
        m_struParam.pInBuffer = ctypes.cast(transInput, ctypes.c_void_p)
        m_struParam.dwInSize = len(transInput)

        M1 = 2 * 1024 * 1024
        buff1 = (ctypes.c_ubyte * M1)()
        m_struParam.pOutBuffer = ctypes.addressof(buff1)
        m_struParam.dwOutSize = M1
        m_struParam.dwRecvTimeOut = 5000  # 接收超时时间，单位毫秒

        user_id = self._cms_user_id()
        reValue = self.cmsDLL.NET_ECMS_ISAPIPassThrough(user_id, ctypes.byref(m_struParam))
        if reValue:
            # 输出参数
            Bbytes_OutBuffer = ctypes.string_at(m_struParam.pOutBuffer, m_struParam.dwOutSize)
            strOutBuffer = str(Bbytes_OutBuffer, 'UTF-8')
            strOutBuffer = strOutBuffer.rstrip('\x00')
            print(strOutBuffer + '\n')
        else:
            # 接口返回失败，错误号错误号判断原因
            print('NET_ECMS_ISAPIPassThrough接口调用失败，错误码：%d，登录句柄：%d' % (
                self.cmsDLL.NET_ECMS_GetLastError(), user_id))

    # 透传接口
    def CMS_XMLRemoteControl(self):
        # 远程控制输入参数
        struRemoteCtrl = NET_EHOME_XML_REMOTE_CTRL_PARAM()
        struRemoteCtrl.dwSize = sizeof(struRemoteCtrl)
        struRemoteCtrl.dwRecvTimeOut = 5000  # 接收超时时间
        struRemoteCtrl.dwSendTimeOut = 5000  # 发送超时时间

        # 获取设备工作状态(比如NVR设备，可以获取IP通道状态)
        inputCfg = """<?xml version="1.0" encoding="UTF-8"?>
            <PPVSPMessage>
            <Version>4.0</Version>
            <Sequence>1</Sequence>
            <CommandType>REQUEST</CommandType>
            <Method>QUERY</Method>
            <Command>GETDEVICEWORKSTATUS</Command>
            <Params>
            </Params>
            </PPVSPMessage>"""

        m_struInbuffer = create_string_buffer(len(inputCfg) + 1)
        m_struInbuffer.value = inputCfg.encode('utf-8')
        struRemoteCtrl.lpInbuffer = cast(m_struInbuffer, c_void_p)
        struRemoteCtrl.dwInBufferSize = sizeof(m_struInbuffer)

        # 输出参数
        m_struOutbuffer = create_string_buffer(5 * 1024)
        struRemoteCtrl.lpOutBuffer = cast(m_struOutbuffer, c_void_p)
        struRemoteCtrl.dwOutBufferSize = sizeof(m_struOutbuffer)

        # 输出状态信息
        m_struStatusBuffer = create_string_buffer(2 * 1024)
        struRemoteCtrl.lpStatusBuffer = cast(m_struStatusBuffer, c_void_p)
        struRemoteCtrl.dwStatusBufferSize = sizeof(m_struStatusBuffer)

        # 提交参数给SDK
        if not self.cmsDLL.NET_ECMS_XMLRemoteControl(self._cms_user_id(), byref(struRemoteCtrl),
                                                     sizeof(struRemoteCtrl)):
            iErr = self.cmsDLL.NET_ECMS_GetLastError()
            print(f"NET_ECMS_XMLRemoteControl failed, error: {iErr}")
            return
        else:
            print("NET_ECMS_XMLRemoteControl succeed：")
            print(f"lpOutBuffer: {m_struOutbuffer.value.decode('utf-8').strip()}")
            print(f"lpStatusBuffer: {m_struStatusBuffer.value.decode('utf-8').strip()}")

    # 录像文件查找
    def FindRecored(self):
        print(sizeof(NET_EHOME_TIME))
        print(sizeof(NET_EHOME_REC_FILE_COND))
        RecFileCond = NET_EHOME_REC_FILE_COND()
        RecFileCond.dwChannel = 1  # 通道号
        RecFileCond.dwRecType = 0xff  # 录像类型 0xff: 全部录像
        RecFileCond.dwStartIndex = 0  # 查询的起始位置，从0开始。
        RecFileCond.dwMaxFileCountPer = 8  # 单次搜索可查询的最大文件数，由实际网络环境决定。建议最大文件数设为8。
        RecFileCond.byLocalOrUTC = 0
        RecFileCond.struStartTime.wYear = 2024
        RecFileCond.struStartTime.byMonth = 9
        RecFileCond.struStartTime.byDay = 3
        RecFileCond.struStartTime.byHour = 0
        RecFileCond.struStartTime.byMinute = 00
        RecFileCond.struStartTime.bySecond = 00
        RecFileCond.struStopTime.wYear = 2024
        RecFileCond.struStopTime.byMonth = 9
        RecFileCond.struStopTime.byDay = 4
        RecFileCond.struStopTime.byHour = 18
        RecFileCond.struStopTime.byMinute = 00
        RecFileCond.struStopTime.bySecond = 00
        FindFileHandle = self.cmsDLL.NET_ECMS_StartFindFile_V11(self._cms_user_id(), ENUM_SEARCH_RECORD_FILE,
                                                                ctypes.byref(RecFileCond), ctypes.sizeof(RecFileCond))
        if FindFileHandle <= -1:
            print(f"NET_ECMS_StartFindFile_V11 error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            return

        while True:
            struFindData = NET_EHOME_REC_FILE()
            struFindData.dwSize = sizeof(struFindData)
            State = self.cmsDLL.NET_ECMS_FindNextFile_V11(FindFileHandle, ctypes.byref(struFindData),
                                                          sizeof(struFindData))
            if State < 0:
                print(f"查找失败，错误码为 : {self.cmsDLL.NET_ECMS_GetLastError()}")
                break
            elif State == 1000:  # 获取文件信息成功
                strFileName = str(struFindData.sFileName, encoding="utf-8").rstrip('\x00')
                print(f"获取文件成功, 文件名称：{strFileName}, 文件大小：{struFindData.dwFileSize}")
                continue
            elif State == 1001:  # 未查找到文件
                print(f"未查找到文件")
                break
            elif State == 1002:  # 正在查找请等待
                print(f"正在查找，请等待")
                continue
            elif State == 1003:  # 没有更多的文件，查找结束
                print(f"没有更多的文件，查找结束")
                break
            elif State == 1005:  # 查找文件超时
                print(f"设备不支持该操作")
                break

        if self.cmsDLL.NET_ECMS_StopFindFile(FindFileHandle):
            print(f"NET_ECMS_StopFindFile suss")
        else:
            print(f"NET_ECMS_StopFindFile error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
        return


