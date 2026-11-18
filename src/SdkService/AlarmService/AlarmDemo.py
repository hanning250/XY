# -*- coding: utf-8 -*-
# @Time : 2023/9/8 10:57
# @Author : qiu jiahang
import ctypes
import os
from ctypes import *
import platform

from src.Common import glo
from src.SdkService.AlarmService.HCISUPAlarm import EHomeMsgCallBack, NET_EHOME_ALARM_LISTEN_PARAM, NET_EHOME_ALARM_MSG, \
    LPNET_EHOME_ALARM_MSG, NET_EHOME_ALARM_ISAPI_INFO, LPNET_EHOME_ALARM_ISAPI_INFO, ams_sdkdllpath, \
    NET_EHOME_EALARM_INIT_CFG_TYPE
from src.SdkService.CmsService.HCISUPCMS import load_library, libeay_dllpath, ssleay_dllpath, strPathCom_dllpath, \
    NET_EHOME_LOCAL_CFG_TYPE, fun_ctype, target_dir


@fun_ctype(c_bool, c_long, POINTER(NET_EHOME_ALARM_MSG), POINTER(c_void_p))
def EHomeMsgCallBack(iHandle, pAlarmMsg, pUser):
    Alarm_struct = ctypes.cast(pAlarmMsg,
                               LPNET_EHOME_ALARM_MSG).contents
    dwType = Alarm_struct.dwAlarmType
    print("AlarmType: ", dwType, ",dwAlarmInfoLen:", Alarm_struct.dwAlarmInfoLen)
    if (Alarm_struct.dwXmlBufLen != 0):
        # 输出参数
        Bbytes_OutBuffer = ctypes.string_at(Alarm_struct.pXmlBuf, Alarm_struct.dwXmlBufLen)
        strOutBuffer = str(Bbytes_OutBuffer, 'UTF-8')
        strOutBuffer = strOutBuffer.rstrip('\x00')
        print('# 输出参数:', strOutBuffer)
    if dwType == 13:
        if (Alarm_struct.dwAlarmInfoLen > 0):
            strISAPIData = ctypes.cast(Alarm_struct.pAlarmInfo, LPNET_EHOME_ALARM_ISAPI_INFO).contents
            if (strISAPIData.dwAlarmDataLen != 0): #Json或者XML数据
                m_strISAPIData = ctypes.string_at(strISAPIData.pAlarmData, strISAPIData.dwAlarmDataLen)
                strOutBuffer = str(m_strISAPIData, 'UTF-8')
                strOutBuffer = strOutBuffer.rstrip('\x00')
                print(strOutBuffer + '\n')
    return True


class amsClass(object):
    '''
    ams服务类
    '''

    def __init__(self):  # __init__() 是类的初始化方法；它在类的实例化操作后会自动调用，不需要手动调用；
        self.iUserID = -1  # 登录句柄
        self.amsHandle = -1  # 监听句柄
        self.cbEHomeMsgCallBack = None
        self.amsDLL = self.loadDLL()
        glo.set_value('amsDLL', self.amsDLL)  # 给全局变量cho，赋值game

    def loadDLL(self):
        '''
        根据操作系统加载sdk动态库
        :return:
        '''
        try:
            print("ams_sdkdllpath: ", ams_sdkdllpath)
            self.amsDLL = load_library(ams_sdkdllpath)
            libeay32_p = ctypes.cast(ctypes.c_char_p(libeay_dllpath.encode()), POINTER(c_void_p))
            ssleay32_p = ctypes.cast(ctypes.c_char_p(ssleay_dllpath.encode()), POINTER(c_void_p))
            self.amsDLL.NET_EALARM_SetSDKInitCfg(NET_EHOME_EALARM_INIT_CFG_TYPE.NET_EHOME_EALARM_INIT_CFG_LIBEAY_PATH.value,
                                               libeay32_p)
            self.amsDLL.NET_EALARM_SetSDKInitCfg(NET_EHOME_EALARM_INIT_CFG_TYPE.NET_EHOME_EALARM_INIT_CFG_SSLEAY_PATH.value,
                                               ssleay32_p)
            self.amsDLL.NET_EALARM_Init()
            strPathCom_p = ctypes.cast(ctypes.c_char_p(strPathCom_dllpath.encode()), POINTER(c_void_p))
            self.amsDLL.NET_EALARM_SetSDKLocalCfg(NET_EHOME_LOCAL_CFG_TYPE.COM_PATH.value, strPathCom_p)

            self.amsDLL.NET_EALARM_SetLogToFile(3, (target_dir + '/IsupSDKLog/').encode('utf-8'), False)  # 日志
            return self.amsDLL
        except OSError as e:
            print('cms 动态库加载失败', e)


    def startAmsListen(self):
        if self.cbEHomeMsgCallBack is None:
            self.cbEHomeMsgCallBack = EHomeMsgCallBack
        net_ehome_alarm_listen_param = NET_EHOME_ALARM_LISTEN_PARAM()
        amsAddress = ctypes.create_string_buffer(glo.get_value("AlarmServerListenIP").encode())
        ctypes.memmove(net_ehome_alarm_listen_param.struAddress.szIP, amsAddress, ctypes.sizeof(amsAddress))
        net_ehome_alarm_listen_param.struAddress.wPort = glo.get_value("AlarmServerListenTCPPort")
        # net_ehome_alarm_listen_param.fnCB = HCISUPAlarm.EHomeMsgCallBack(self.cbEHomeMsgCallBack)
        net_ehome_alarm_listen_param.fnMsgCb = self.cbEHomeMsgCallBack
        net_ehome_alarm_listen_param.byProtocolType = glo.get_value('AlarmServerType')
        self.amsHandle = self.amsDLL.NET_EALARM_StartListen(ctypes.byref(net_ehome_alarm_listen_param))
        if self.amsHandle < 0:
            print('NET_EALARM_StartListen failed, error code: ', self.amsDLL.NET_EALARM_GetLastError())
        else:
            # print(type(net_ehome_alarm_listen_param.struAddress.szIP))
            print('报警服务器: ', str(net_ehome_alarm_listen_param.struAddress.szIP, encoding="utf-8").rstrip(
                '\x00') + '_' + str(net_ehome_alarm_listen_param.struAddress.wPort))

    def stopAmsListen(self):
        if self.amsHandle > -1:
            self.amsDLL.NET_EALARM_StopListen(self.amsHandle)
            self.amsDLL.NET_EALARM_Fini()
