# -*- coding: utf-8 -*-
# @Time : 2023/9/8 11:03
# @Author : qiu jiahang
import ctypes
import os
import threading
from ctypes import *
from datetime import datetime

from src.Common import glo
from src.Common.ListenHelper import bind_ip_address
from src.Common.SdkInit import configure_com_path, configure_openssl, configure_sdk_log
from src.SdkService.CmsService.HCISUPCMS import load_library, \
    NET_EHOME_LOCAL_CFG_TYPE, target_dir, NET_EHOME_PREVIEWINFO_IN, NET_EHOME_PREVIEWINFO_OUT, \
    NET_EHOME_PUSHSTREAM_IN, NET_EHOME_PUSHSTREAM_OUT
from src.SdkService.StreamService.HCISUPStream import *


def _fill_ehome_time(time_struct, dt):
    time_struct.wYear = dt.year
    time_struct.byMonth = dt.month
    time_struct.byDay = dt.day
    time_struct.byHour = dt.hour
    time_struct.byMinute = dt.minute
    time_struct.bySecond = dt.second


def _new_output_path(subdir, label):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return os.path.join(target_dir, 'outputFiles', subdir, f'{ts}_{label}.mp4')


class smsClass(object):
    @staticmethod
    def _resolve_user_id(user_id=None, stored_user_id=-1):
        if user_id is not None:
            return user_id
        if stored_user_id >= 0:
            return stored_user_id
        return glo.get_value('iUserID')

    def __init__(self):
        self.smsDLL = self.loadDLL()  # 初始化sdk
        self.cmsDLL = glo.get_value('cmsDLL')
        self.previewListenHandle = -1  # 预览监听句柄
        self.playbackListenHandle = -1  # 回放监听句柄
        self.backSessionID = -1  # 回放sessionID
        self.previewUserID = -1  # 本次预览使用的登录句柄
        self.playbackUserID = -1  # 本次回放使用的登录句柄
        self.lPreviewHandle = -1  # 预览句柄
        self.m_lPlayBackLinkHandle = -1  # 回放句柄
        self.fPREVIEW_NEWLINK_CB_FILE = PREVIEW_NEWLINK_CB(self.FPREVIEW_NEWLINK_CB_FILE)
        self.fPREVIEW_DATA_CB_FILE = PREVIEW_DATA_CB(self.FPREVIEW_DATA_CB_FILE)
        self.fPLAYBACK_NEWLINK_CB_FILE = PLAYBACK_NEWLINK_CB(self.PLAYBACK_NEWLINK_CB_FILE)
        self.fPLAYBACK_DATA_CB_FILE = PLAYBACK_DATA_CB(self.PLAYBACK_DATA_CB_FILE)

        self._preview_count = 0  # 降低回调打印频率使用
        self._playback_count = 0
        self.preview_file_path = ''
        self.playbackFile = ''
        self._preview_fp = None
        self._playback_fp = None
        self._file_lock = threading.Lock()
        glo.set_value('smsDLL', self.smsDLL)

    def loadDLL(self):
        '''
        根据操作系统加载sdk动态库
        :return:
        '''
        try:
            print("sms_sdkdllpath: ", sms_sdkdllpath)
            self.smsDLL = load_library(sms_sdkdllpath)
            configure_openssl(
                self.smsDLL,
                self.smsDLL.NET_ESTREAM_SetSDKInitCfg,
                NET_EHOME_ESTREAM_INIT_CFG_TYPE.NET_EHOME_ESTREAM_INIT_CFG_LIBEAY_PATH.value,
                NET_EHOME_ESTREAM_INIT_CFG_TYPE.NET_EHOME_ESTREAM_INIT_CFG_SSLEAY_PATH.value,
            )
            self.smsDLL.NET_ESTREAM_Init()
            configure_com_path(self.smsDLL, self.smsDLL.NET_ESTREAM_SetSDKLocalCfg, NET_EHOME_LOCAL_CFG_TYPE.COM_PATH.value)
            configure_sdk_log(self.smsDLL, self.smsDLL.NET_ESTREAM_SetLogToFile)
            return self.smsDLL
        except OSError as e:
            print('sms 动态库加载失败', e)

    def _ensure_listen(self, handle_attr, ip_key, port_key, start_fn, setup_listen_cfg, started_label):
        endpoint = f"{glo.get_value(ip_key)}_{glo.get_value(port_key)}"
        if getattr(self, handle_attr) >= 0:
            print(f'{started_label}监听已开启: {endpoint}')
            return

        handle = start_fn(ctypes.byref(setup_listen_cfg()))
        setattr(self, handle_attr, handle)
        if handle < 0:
            print(f'{start_fn.__name__} Fail, err code: {self.smsDLL.NET_ESTREAM_GetLastError()}')
        else:
            print(f'{started_label}服务器: {endpoint}')

    def startRealPlayListen_File(self):
        """开启sms服务监听（原始码流写文件）"""
        def setup_listen_cfg():
            stru_preview_listen = NET_EHOME_LISTEN_PREVIEW_CFG()
            bind_ip_address(stru_preview_listen.struIPAdress, "SmsServerListenIP", "SmsServerListenPort")
            stru_preview_listen.pUser = None
            stru_preview_listen.byLinkMode = 0
            stru_preview_listen.fnNewLinkCB = self.fPREVIEW_NEWLINK_CB_FILE
            return stru_preview_listen

        self._ensure_listen(
            'previewListenHandle', 'SmsServerListenIP', 'SmsServerListenPort',
            self.smsDLL.NET_ESTREAM_StartListenPreview, setup_listen_cfg, '预览流媒体')

    def startPlayBackListen_FILE(self):
        """按时间回放-开启sms服务监听（原始码流写文件）"""
        def setup_listen_cfg():
            stru_playback_listen = NET_EHOME_PLAYBACK_LISTEN_PARAM()
            bind_ip_address(stru_playback_listen.struIPAdress, "SmsBackServerListenIP", "SmsBackServerListenPort")
            stru_playback_listen.byLinkMode = 0
            stru_playback_listen.fnNewLinkCB = self.fPLAYBACK_NEWLINK_CB_FILE
            return stru_playback_listen

        self._ensure_listen(
            'playbackListenHandle', 'SmsBackServerListenIP', 'SmsBackServerListenPort',
            self.smsDLL.NET_ESTREAM_StartListenPlayBack, setup_listen_cfg, '回放流媒体')

    def _begin_output_session(self, path_attr, fp_attr, subdir, label):
        self._end_output_session(fp_attr)
        path = _new_output_path(subdir, label)
        setattr(self, path_attr, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        setattr(self, fp_attr, open(path, 'wb'))
        return path

    def _end_output_session(self, fp_attr):
        fp = getattr(self, fp_attr)
        if fp:
            fp.close()
            setattr(self, fp_attr, None)

    # 将视频流保存到本地（SDK 回调可能并发，需加锁且复用会话文件句柄）
    def writeFile(self, filePath, pBuffer, dwBufSize):
        if not filePath:
            return

        data_array = (c_byte * dwBufSize)()
        memmove(data_array, pBuffer, dwBufSize)
        data = bytes(data_array)

        session_fp = None
        if filePath == self.playbackFile:
            session_fp = self._playback_fp
        elif filePath == self.preview_file_path:
            session_fp = self._preview_fp

        try:
            with self._file_lock:
                if session_fp:
                    session_fp.write(data)
                    return
                os.makedirs(os.path.dirname(filePath), exist_ok=True)
                with open(filePath, 'ab') as output_file:
                    output_file.write(data)
        except OSError as e:
            print(f'写入视频文件失败: {filePath}, 错误: {e}')

    def stopSmsListen(self):
        """sms服务停止监听"""
        self._end_output_session('_preview_fp')
        self._end_output_session('_playback_fp')
        if self.previewListenHandle > -1:
            self.smsDLL.NET_ESTREAM_StopListenPreview(self.previewListenHandle)
            self.previewListenHandle = -1
        if self.playbackListenHandle > -1:
            self.smsDLL.NET_ESTREAM_StopListenPlayBack(self.playbackListenHandle)
            self.playbackListenHandle = -1
        self.smsDLL.NET_ESTREAM_Fini()

    def FPREVIEW_DATA_CB_FILE(self, iPreviewHandle, pPreviewCBMsg, pUserData):
        pPreviewCBMsg = cast(pPreviewCBMsg, LPNET_EHOME_PREVIEW_CB_MSG).contents
        if self._preview_count == 100:  # 降低打印频率
            print(f"FPREVIEW_DATA_CB callback, data length: {pPreviewCBMsg.dwDataLen}")
            self._preview_count = 0
        self._preview_count += 1

        if pPreviewCBMsg.byDataType == 1:
            pass
        elif pPreviewCBMsg.byDataType == 2:
            self.writeFile(self.preview_file_path, pPreviewCBMsg.pRecvdata, pPreviewCBMsg.dwDataLen)
        else:
            print(u'其他数据,长度:', pPreviewCBMsg.dwDataLen)

    def PLAYBACK_DATA_CB_FILE(self, iPlayBackLinkHandle, pDataCBInfo, pUserData):
        pDataCBInfo = cast(pDataCBInfo, LPNET_EHOME_PLAYBACK_DATA_CB_INFO).contents
        if self._playback_count == 100:  # 降低打印频率
            print(f"FPLAYBACK_DATA_CB callback , dwDataLen: {pDataCBInfo.dwDataLen},dwType:{pDataCBInfo.dwType}")
            self._playback_count = 0
        self._playback_count += 1

        if pDataCBInfo.dwType == 1:
            glo.set_value("stopPlayBackFlag", False)
        elif pDataCBInfo.dwType == 3:
            print("收到回放结束信令！")
            glo.set_value("stopPlayBackFlag", True)
        elif pDataCBInfo.dwType == 2:
            self.writeFile(self.playbackFile, pDataCBInfo.pData, pDataCBInfo.dwDataLen)
        else:
            print(u'其他数据,长度:', pDataCBInfo.dwDataLen)

    def FPREVIEW_NEWLINK_CB_FILE(self, lLinkHandle, pNewLinkCBMsg, pUserData):
        print("FPREVIEW_NEWLINK_CB_File callback")
        self.lPreviewHandle = lLinkHandle
        struDataCB = NET_EHOME_PREVIEW_DATA_CB_PARAM()
        struDataCB.fnPreviewDataCB = self.fPREVIEW_DATA_CB_FILE
        if self.smsDLL.NET_ESTREAM_SetPreviewDataCB(lLinkHandle, struDataCB) is False:
            print("NET_ESTREAM_SetPreviewDataCB failed err:：", self.smsDLL.NET_ESTREAM_GetLastError())
            return False
        return True

    def PLAYBACK_NEWLINK_CB_FILE(self, lPlayBackLinkHandle, pNewLinkCBInfo, pUserData):
        pNewLinkCBInfo = cast(pNewLinkCBInfo, LPNET_EHOME_PLAYBACK_NEWLINK_CB_INFO).contents
        szDeviceID = str(pNewLinkCBInfo.szDeviceID, encoding="utf-8").rstrip('\x00')
        print(
            f"PLAYBACK_NEWLINK_CB callback, szDeviceID:{szDeviceID} ,lSessionID:{pNewLinkCBInfo.iSessionID}, dwChannelNo:{pNewLinkCBInfo.dwChannelNo}")
        self.m_lPlayBackLinkHandle = lPlayBackLinkHandle
        struCBParam = NET_EHOME_PLAYBACK_DATA_CB_PARAM()
        struCBParam.fnPlayBackDataCB = self.fPLAYBACK_DATA_CB_FILE
        struCBParam.byStreamFormat = 0
        if self.smsDLL.NET_ESTREAM_SetPlayBackDataCB(lPlayBackLinkHandle, struCBParam) is False:
            print("NET_ESTREAM_SetPlayBackDataCB failed err:：", self.smsDLL.NET_ESTREAM_GetLastError())
            return False
        return True

    def RealPlay(self, channel, user_id=None):
        self.previewUserID = self._resolve_user_id(user_id)
        self.preview_file_path = self._begin_output_session(
            'preview_file_path', '_preview_fp', 'preview', 'previewVideo')
        print(f'预览保存路径: {self.preview_file_path}')
        struPreviewIn = NET_EHOME_PREVIEWINFO_IN()
        struPreviewIn.iChannel = channel  # 预览通道号
        struPreviewIn.dwLinkMode = 0  # 0 - TCP方式，1 - UDP方式
        struPreviewIn.dwStreamType = 0  # 码流类型：0 - 主码流，1 - 子码流, 2 - 第三码流

        bind_ip_address(struPreviewIn.struStreamSever, "SmsServerIP", "SmsServerPort")
        struPreviewOut = NET_EHOME_PREVIEWINFO_OUT()
        getRS = self.cmsDLL.NET_ECMS_StartGetRealStream(self.previewUserID, ctypes.byref(struPreviewIn),
                                                        ctypes.byref(struPreviewOut))
        if getRS:
            print(f"NET_ECMS_StartGetRealStream succeed, sessionID: {struPreviewOut.lSessionID}, lUserID: {self.previewUserID}")
            self.sessionID = struPreviewOut.lSessionID
        else:
            print(f"NET_ECMS_StartGetRealStream failed, error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            return

        struPushInfoIn = NET_EHOME_PUSHSTREAM_IN()
        struPushInfoIn.dwSize = sizeof(struPushInfoIn)
        struPushInfoIn.lSessionID = self.sessionID

        struPushInfoOut = NET_EHOME_PUSHSTREAM_OUT()
        struPushInfoOut.dwSize = sizeof(struPushInfoOut)

        if self.cmsDLL.NET_ECMS_StartPushRealStream(self.previewUserID, struPushInfoIn,
                                                    struPushInfoOut) is False:
            print(f"NET_ECMS_StartPushRealStream failed, error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            return
        else:
            print(f"NET_ECMS_StartPushRealStream succeed, sessionID: {struPushInfoIn.lSessionID}, lUserID: {self.previewUserID}")

    def StopRealPlay(self):
        if self.smsDLL.NET_ESTREAM_StopPreview(self.lPreviewHandle):
            print(f"NET_ESTREAM_StopPreview succ ")
        else:
            print(f"NET_ESTREAM_StopPreview failed, error code: {self.smsDLL.NET_ESTREAM_GetLastError()}")
            return
        print("停止Stream的实时流转发")

        if self.cmsDLL.NET_ECMS_StopGetRealStream(self.previewUserID, self.sessionID):
            print(f"NET_ECMS_StopGetRealStream succ ")
        else:
            print(f"NET_ECMS_StopGetRealStream failed,err =  {self.cmsDLL.NET_ECMS_GetLastError()}")
            return
        print("CMS发送预览停止请求")
        self._end_output_session('_preview_fp')

    def PlayBackByTime(self, lchannel, minutes=1, user_id=None):
        self.playbackUserID = self._resolve_user_id(user_id)
        self.playbackFile = self._begin_output_session(
            'playbackFile', '_playback_fp', 'back', 'playbackVideo')
        print(f'回放保存路径: {self.playbackFile}')
        m_struPlayBackInfoIn = NET_EHOME_PLAYBACK_INFO_IN()
        m_struPlayBackInfoIn.dwSize = sizeof(m_struPlayBackInfoIn)
        m_struPlayBackInfoIn.dwChannel = lchannel  # 通道号
        m_struPlayBackInfoIn.byPlayBackMode = 1  # 0 - 按文件名回放，1 - 按时间回放

        stop_dt = datetime.now()
        start_dt = datetime.fromtimestamp(stop_dt.timestamp() - minutes * 60)
        play_back_by_time = NET_EHOME_PLAYBACKBYTIME()
        _fill_ehome_time(play_back_by_time.struStartTime, start_dt)
        _fill_ehome_time(play_back_by_time.struStopTime, stop_dt)
        print(f'回放时间段: {start_dt} ~ {stop_dt}')

        m_struPlayBackInfoIn.unionPlayBackMode.struPlayBackbyTime = play_back_by_time

        bind_ip_address(m_struPlayBackInfoIn.struStreamSever, "SmsBackServerIP", "SmsBackServerPort")

        m_struPlayBackInfoOut = NET_EHOME_PLAYBACK_INFO_OUT()

        if self.cmsDLL.NET_ECMS_StartPlayBack(self.playbackUserID, ctypes.byref(m_struPlayBackInfoIn),
                                              ctypes.byref(m_struPlayBackInfoOut)):
            print(f"NET_ECMS_StartPlayBack succeed, lSessionID: {m_struPlayBackInfoOut.lSessionID}, lUserID: {self.playbackUserID}")
        else:
            print(f"NET_ECMS_StartPlayBack failed, error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            return False

        m_struPushPlayBackIn = NET_EHOME_PUSHPLAYBACK_IN()
        m_struPushPlayBackIn.dwSize = sizeof(m_struPushPlayBackIn)
        m_struPushPlayBackIn.lSessionID = m_struPlayBackInfoOut.lSessionID
        self.backSessionID = m_struPushPlayBackIn.lSessionID

        m_struPushPlayBackOut = NET_EHOME_PUSHPLAYBACK_OUT()
        m_struPushPlayBackOut.dwSize = sizeof(m_struPushPlayBackOut)

        if self.cmsDLL.NET_ECMS_StartPushPlayBack(self.playbackUserID, ctypes.byref(m_struPushPlayBackIn),
                                                  ctypes.byref(m_struPushPlayBackOut)):
            print(
                f"NET_ECMS_StartPushPlayBack succeed, sessionID: {m_struPushPlayBackIn.lSessionID}, lUserID: {self.playbackUserID}")
        else:
            print(f"NET_ECMS_StartPushPlayBack failed, error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            return False
        return True

    def stopPlayBackByTime(self):
        if not self.cmsDLL.NET_ECMS_StopPlayBack(self.playbackUserID, self.backSessionID):
            print(f"NET_ECMS_StopPlayBack failed,err = {self.cmsDLL.NET_ECMS_GetLastError()}")
            return
        print("CMS发送回放停止请求")

        if not self.smsDLL.NET_ESTREAM_StopPlayBack(self.m_lPlayBackLinkHandle):
            print(f"NET_ESTREAM_StopPlayBack failed,err =  {self.smsDLL.NET_ESTREAM_GetLastError()}")
            return
        print("停止回放Stream服务的实时流转发")
        self._end_output_session('_playback_fp')
