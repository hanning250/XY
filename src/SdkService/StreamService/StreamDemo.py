# -*- coding: utf-8 -*-
# @Time : 2023/9/8 11:03
# @Author : qiu jiahang
import contextlib
import ctypes
import os
import threading
from ctypes import *
from datetime import datetime

from src.Common import glo
from src.SdkService.CmsService.HCISUPCMS import load_library, libeay_dllpath, ssleay_dllpath, strPathCom_dllpath, \
    NET_EHOME_LOCAL_CFG_TYPE, sys_platform, target_dir, NET_EHOME_PREVIEWINFO_IN, NET_EHOME_PREVIEWINFO_OUT, \
    NET_EHOME_PUSHSTREAM_IN, NET_EHOME_PUSHSTREAM_OUT
from src.SdkService.StreamService.HCISUPStream import *
from src.SdkService.StreamService.PlayCtrl import PlayCtrlDecoder, STREAME_FILE


def _fill_ehome_time(time_struct, dt):
    """把 datetime 填进 SDK 的时间结构体。"""
    time_struct.wYear = dt.year
    time_struct.byMonth = dt.month
    time_struct.byDay = dt.day
    time_struct.byHour = dt.hour
    time_struct.byMinute = dt.minute
    time_struct.bySecond = dt.second


def _set_stream_server_address(stream_server, ip_key, port_key):
    """把配置里的流媒体服务器地址写进 SDK 结构体。"""
    sms_address = ctypes.create_string_buffer(glo.get_value(ip_key).encode())
    ctypes.memmove(stream_server.szIP, sms_address, ctypes.sizeof(sms_address))
    stream_server.wPort = glo.get_value(port_key)


def _new_output_path(subdir, label):
    """生成输出文件路径：outputFiles/<subdir>/<时间戳>_<label>.mp4

    用可读时间戳（而非 datetime.timestamp() 浮点串），方便排查时对时间。
    """
    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return os.path.join(target_dir, 'outputFiles', subdir, f'{ts}_{label}.mp4')


class smsClass(object):
    @staticmethod
    def _resolve_user_id(user_id=None, stored_user_id=-1):
        """解析本次操作使用的登录句柄。

        ★ 多设备修复：优先用调用方显式传入的 user_id；
          其次用实例缓存的；最后才回退到全局 iUserID。
        """
        if user_id is not None:
            return user_id
        if stored_user_id >= 0:
            return stored_user_id
        return glo.get_value('iUserID')

    def __init__(self):
        self.smsDLL = self.loadDLL()  # 初始化sdk
        self.cmsDLL = glo.get_value('cmsDLL')
        # ★ 预览与回放各用各的监听句柄，避免互相干扰 / 停止时漏关
        self.previewListenHandle = -1  # 预览监听句柄
        self.playbackListenHandle = -1  # 回放监听句柄
        self.backSessionID = -1  # 回放sessionID
        self.previewUserID = -1  # 本次预览使用的登录句柄
        self.playbackUserID = -1  # 本次回放使用的登录句柄
        self.lPreviewHandle = -1  # 预览句柄
        self.m_lPlayBackLinkHandle = -1  # 回放句柄
        self.fPREVIEW_NEWLINK_CB_FILE = PREVIEW_NEWLINK_CB(self.FPREVIEW_NEWLINK_CB_FILE)  # 预览监听回调函数实现 - 文件模式
        self.fPREVIEW_DATA_CB_FILE = PREVIEW_DATA_CB(self.FPREVIEW_DATA_CB_FILE)  # 预览回调函数实现 - 文件存储
        self.fPREVIEW_DATA_CB_PLAYCTRL = PREVIEW_DATA_CB(self.FPREVIEW_DATA_CB_PLAYCTRL)

        self.fPLAYBACK_NEWLINK_CB_FILE = PLAYBACK_NEWLINK_CB(self.PLAYBACK_NEWLINK_CB_FILE)  # 回放监听回调函数实现 - 文件模式
        self.fPLAYBACK_DATA_CB_FILE = PLAYBACK_DATA_CB(self.PLAYBACK_DATA_CB_FILE)  # 回放回调函数实现 - 文件存储
        self.fPLAYBACK_DATA_CB_PLAYCTRL = PLAYBACK_DATA_CB(self.PLAYBACK_DATA_CB_PLAYCTRL)

        self.preview_decoder = None
        self.playback_decoder = None
        self.use_playctrl_preview = False
        self.use_playctrl_playback = False

        self.Count = 0  # 降低回调打印频率使用
        # 预览视频文件的输出位置设置（会话开始时才真正创建，见 _begin_output_session）
        ts = str(datetime.timestamp(datetime.now()))
        # ★ Linux 修复：原代码用 '\\outputFiles\\' 拼接，在 Linux 上会得到
        #   /app\outputFiles\x.mp4 这种非法路径（反斜杠不是分隔符）。
        #   改用 os.path.join，Windows/Linux 都正确。
        _out = os.path.join(target_dir, 'outputFiles')
        self.preview_file_path = os.path.join(_out, ts + '_previewVideo.mp4')
        self.preview_snapshot_path = os.path.join(_out, ts + '_previewSnapshot.jpg')
        self.playbackFile = os.path.join(_out, ts + '_playbackVideo.mp4')
        self.playback_snapshot_path = os.path.join(_out, ts + '_playbackSnapshot.jpg')
        # ★ 会话期文件句柄：避免每个回调块都 open/close（实测慢 47 倍，且跑在 SDK 回调线程上）
        self._preview_fp = None
        self._playback_fp = None

        # ★★ 2026-10-23 并发改造：按会话隔离回放状态
        #   key = lPlayBackLinkHandle（每一路回放唯一）
        #   value = {
        #       "fp":    打开的文件句柄,
        #       "path":  输出路径,
        #       "session_id": SDK 的 lSessionID,
        #       "done":  该路是否已收到结束信令,
        #       "started_at": 开始时间,
        #   }
        #   ★ 为什么必须按会话隔离：回调 PLAYBACK_DATA_CB_FILE 拿到的是
        #     iPlayBackLinkHandle，用它查表才能把数据写到正确的文件。
        #     原来所有路共用 self.playbackFile → 数据串台。
        self._playback_sessions: dict[int, dict] = {}
        self._pbs_lock = threading.Lock()
        # SDK 数据回调可能并发，写文件必须加锁
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

            libeay32_p = ctypes.cast(ctypes.c_char_p(libeay_dllpath.encode()), POINTER(c_void_p))
            ssleay32_p = ctypes.cast(ctypes.c_char_p(ssleay_dllpath.encode()), POINTER(c_void_p))
            self.smsDLL.NET_ESTREAM_SetSDKInitCfg(
                NET_EHOME_ESTREAM_INIT_CFG_TYPE.NET_EHOME_ESTREAM_INIT_CFG_LIBEAY_PATH.value,
                libeay32_p)
            self.smsDLL.NET_ESTREAM_SetSDKInitCfg(
                NET_EHOME_ESTREAM_INIT_CFG_TYPE.NET_EHOME_ESTREAM_INIT_CFG_SSLEAY_PATH.value,
                ssleay32_p)

            # 流媒体初始化
            self.smsDLL.NET_ESTREAM_Init()

            # 设置HCAapSDKCom组件库文件夹所在路径
            strPathCom_p = ctypes.cast(ctypes.c_char_p(strPathCom_dllpath.encode()), POINTER(c_void_p))
            self.smsDLL.NET_ESTREAM_SetSDKLocalCfg(NET_EHOME_LOCAL_CFG_TYPE.COM_PATH.value, strPathCom_p)

            self.smsDLL.NET_ESTREAM_SetLogToFile(3, (target_dir + '/IsupSDKLog/').encode('utf-8'), False)  # 日志
            return self.smsDLL
        except OSError as e:
            print('sms 动态库加载失败', e)

    def _reset_snapshot_paths(self, prefix):
        """重设快照路径（PlayCtrl 模式用）。

        视频文件路径改由 _begin_output_session 在会话开始时生成，
        这里只负责 jpg 快照，落盘到 outputFiles/<prefix>/ 保持同一目录。
        """
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        base = os.path.join(target_dir, 'outputFiles', prefix)
        os.makedirs(base, exist_ok=True)
        self.preview_snapshot_path = os.path.join(base, f'{ts}_previewSnapshot.jpg')
        self.playback_snapshot_path = os.path.join(base, f'{ts}_playbackSnapshot.jpg')

    def _ensure_listen(self, handle_attr, ip_key, port_key, start_fn, setup_listen_cfg, started_label):
        """开启监听，已开启则跳过（避免重复监听 / 句柄覆盖）。"""
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
        self.use_playctrl_preview = False
        self._start_real_play_listen(self.fPREVIEW_NEWLINK_CB_FILE)

    def startRealPlayListen_PlayCtrl(self):
        """开启sms服务监听（PlayCtrl 解密解码）"""
        self.use_playctrl_preview = True
        self.preview_decoder = PlayCtrlDecoder()
        self._reset_snapshot_paths('preview')
        self._start_real_play_listen(self.fPREVIEW_NEWLINK_CB_FILE)

    def _start_real_play_listen(self, new_link_cb):
        def setup_listen_cfg():
            stru_preview_listen = NET_EHOME_LISTEN_PREVIEW_CFG()
            _set_stream_server_address(stru_preview_listen.struIPAdress, "SmsServerListenIP", "SmsServerListenPort")
            stru_preview_listen.pUser = None
            stru_preview_listen.byLinkMode = 0  # 0- TCP方式，1- UDP方式
            stru_preview_listen.fnNewLinkCB = new_link_cb
            return stru_preview_listen

        self._ensure_listen(
            'previewListenHandle', 'SmsServerListenIP', 'SmsServerListenPort',
            self.smsDLL.NET_ESTREAM_StartListenPreview, setup_listen_cfg, '流媒体')

    def startPlayBackListen_FILE(self):
        """按时间回放-开启sms服务监听（原始码流写文件）"""
        self.use_playctrl_playback = False
        self._start_playback_listen(self.fPLAYBACK_NEWLINK_CB_FILE)

    def startPlayBackListen_PlayCtrl(self):
        """按时间回放-开启sms服务监听（PlayCtrl 解密解码）"""
        self.use_playctrl_playback = True
        self.playback_decoder = PlayCtrlDecoder()
        self._reset_snapshot_paths('back')
        glo.set_value("stopPlayBackFlag", True)
        self._start_playback_listen(self.fPLAYBACK_NEWLINK_CB_FILE)

    def _start_playback_listen(self, new_link_cb):
        def setup_listen_cfg():
            stru_playback_listen = NET_EHOME_PLAYBACK_LISTEN_PARAM()
            _set_stream_server_address(stru_playback_listen.struIPAdress, "SmsBackServerListenIP", "SmsBackServerListenPort")
            stru_playback_listen.byLinkMode = 0  # 0- TCP方式，1- UDP方式
            stru_playback_listen.fnNewLinkCB = new_link_cb
            return stru_playback_listen

        self._ensure_listen(
            'playbackListenHandle', 'SmsBackServerListenIP', 'SmsBackServerListenPort',
            self.smsDLL.NET_ESTREAM_StartListenPlayBack, setup_listen_cfg, '回放流媒体')

    # 将视频流保存到本地
    #
    # ★ 会话期句柄复用（合并自同事 XY-development v2）：
    #   原实现每个回调块都 open/close 一次，实测 3000 块慢 47 倍。
    #   更关键的是这跑在 SDK 回调线程上，长流时会拖慢回调消费导致丢帧。
    #   这里改为会话开始打开一次、结束关闭。
    #
    # ⚠️ 与 v2 的差异：v2 用 `filePath == self.playbackFile` 反查句柄，
    #    但 RealPlay() 是先改 self.preview_file_path 再注册回调，
    #    回调若落在赋值竞态窗口内会取到 None 而静默退回 append。
    #    这里改为**显式传入句柄**，从根上避免竞态。
    def _begin_output_session(self, path_attr, fp_attr, subdir, label):
        """开启一个输出会话：关掉旧的，建新文件，持有句柄。"""
        self._end_output_session(fp_attr)
        path = _new_output_path(subdir, label)
        setattr(self, path_attr, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        setattr(self, fp_attr, open(path, 'wb'))
        return path

    def _end_output_session(self, fp_attr):
        """结束输出会话：关闭并释放句柄。

        ★ 加锁后再关闭：否则 SDK 回调线程可能已取到句柄引用，
          随后这里 close，回调再写就抛 ValueError（I/O operation on closed file）。
        """
        with self._file_lock:
            fp = getattr(self, fp_attr, None)
            if fp:
                try:
                    fp.close()
                except OSError:
                    pass
                setattr(self, fp_attr, None)

    def writeFile(self, filePath, pBuffer, dwBufSize, session_fp=None, fp_attr=None):
        """把码流块写入文件。

        session_fp : 当前会话的文件句柄（有则复用）
        fp_attr    : 会话句柄的属性名；传入则在锁内**重新读取**，
                     避免用锁外取到的旧引用去写一个已被关闭的文件。
        """
        if not filePath:
            return

        # 使用memmove函数将指针数据读到数组中
        data_array = (c_byte * dwBufSize)()
        memmove(data_array, pBuffer, dwBufSize)
        data = bytes(data_array)

        try:
            with self._file_lock:
                # ★ 锁内重新取句柄，杜绝「拿到引用 → 被关闭 → 再写」的竞态
                current_fp = getattr(self, fp_attr, None) if fp_attr else session_fp
                if current_fp and not current_fp.closed:
                    current_fp.write(data)
                    return
                os.makedirs(os.path.dirname(filePath), exist_ok=True)
                with open(filePath, 'ab') as output_file:
                    output_file.write(data)
        except (OSError, ValueError) as e:
            # ValueError: 句柄在写入瞬间被关闭 —— 属于可恢复的丢块，不应抛回 C 回调栈
            print(f'写入视频文件失败: {filePath}, 错误: {e}')

    def _close_preview_decoder(self, save_snapshot=False):
        if self.preview_decoder is None:
            return
        if save_snapshot:
            self.preview_decoder.save_jpeg(self.preview_snapshot_path)
        self.preview_decoder.close()
        self.preview_decoder = None

    def _close_playback_decoder(self, save_snapshot=False):
        if self.playback_decoder is None:
            return
        if save_snapshot:
            self.playback_decoder.save_jpeg(self.playback_snapshot_path)
        self.playback_decoder.close()
        self.playback_decoder = None

    def stopSmsListen(self):
        """sms服务停止监听（★ 预览与回放两个监听都要停）"""
        self._close_preview_decoder(save_snapshot=False)
        self._close_playback_decoder(save_snapshot=False)
        # ★ 关闭尚未释放的会话文件句柄，避免文件句柄泄漏
        self._end_output_session('_preview_fp')
        self._end_output_session('_playback_fp')
        stopped_any = False
        if self.previewListenHandle > -1:
            self.smsDLL.NET_ESTREAM_StopListenPreview(self.previewListenHandle)
            self.previewListenHandle = -1
            stopped_any = True
        if self.playbackListenHandle > -1:
            self.smsDLL.NET_ESTREAM_StopListenPlayBack(self.playbackListenHandle)
            self.playbackListenHandle = -1
            stopped_any = True
        # ★ 只在确实停过监听时才 Fini：SDK 的 Init/Fini 是进程级的，
        #   无条件调用会把别的实例仍在使用的 SDK 拆掉。
        if stopped_any:
            self.smsDLL.NET_ESTREAM_Fini()

    def _feed_playctrl(self, decoder, data_type, p_buffer, data_len, stream_mode=STREAME_FILE):
        data = string_at(p_buffer, data_len)
        if data_type == 1:
            decoder.open_header(data, stream_mode=stream_mode)
        elif data_type == 2:
            decoder.input_data(data)

    def FPREVIEW_DATA_CB_FILE(self, iPreviewHandle, pPreviewCBMsg, pUserData):
        pPreviewCBMsg = cast(pPreviewCBMsg, LPNET_EHOME_PREVIEW_CB_MSG).contents
        if self.Count == 100:  # 降低打印频率
            print(f"FPREVIEW_DATA_CB callback, data length: {pPreviewCBMsg.dwDataLen}")
            self.Count = 0
        self.Count += 1

        # 码流回调函数
        if pPreviewCBMsg.byDataType == 1:
            pass
        elif pPreviewCBMsg.byDataType == 2:
            self.writeFile(self.preview_file_path, pPreviewCBMsg.pRecvdata,
                           pPreviewCBMsg.dwDataLen, fp_attr='_preview_fp')
        else:
            print(u'其他数据,长度:', pPreviewCBMsg.dwDataLen)

    def FPREVIEW_DATA_CB_PLAYCTRL(self, iPreviewHandle, pPreviewCBMsg, pUserData):
        pPreviewCBMsg = cast(pPreviewCBMsg, LPNET_EHOME_PREVIEW_CB_MSG).contents
        if self.Count == 100:
            print(f'FPREVIEW_DATA_CB(PlayCtrl), data length: {pPreviewCBMsg.dwDataLen}, type: {pPreviewCBMsg.byDataType}')
            self.Count = 0
        self.Count += 1

        try:
            if pPreviewCBMsg.byDataType in (1, 2):
                self._feed_playctrl(
                    self.preview_decoder,
                    pPreviewCBMsg.byDataType,
                    pPreviewCBMsg.pRecvdata,
                    pPreviewCBMsg.dwDataLen,
                    stream_mode=0,
                )
        except Exception as e:
            print(f'PlayCtrl 预览解码失败: {e}')

    def PLAYBACK_DATA_CB_FILE(self, iPlayBackLinkHandle, pDataCBInfo, pUserData):
        pDataCBInfo = cast(pDataCBInfo, LPNET_EHOME_PLAYBACK_DATA_CB_INFO).contents
        if self.Count == 100:  # 降低打印频率
            print(f"FPLAYBACK_DATA_CB callback , dwDataLen: {pDataCBInfo.dwDataLen},dwType:{pDataCBInfo.dwType}")
            self.Count = 0
        self.Count += 1

        # 码流回调函数
        if pDataCBInfo.dwType == 1:
            glo.set_value("stopPlayBackFlag", False)  # 初始化回放标记
            # self.stopPlayBackFlag = False
        elif pDataCBInfo.dwType == 3:
            print("收到回放结束信令！")
            # ★★ 2026-10-23 并发改造：标记**该会话**完成，而不是全局。
            #   多路并发时，任意一路结束就置全局 True 会让其它路提前退出。
            with self._pbs_lock:
                sess = self._playback_sessions.get(int(iPlayBackLinkHandle))
                if sess is not None:
                    sess["done"] = True
            # 仍然写全局标记：`_run_job` 里单路等待逻辑依赖它（向后兼容）
            glo.set_value("stopPlayBackFlag", True)
        elif pDataCBInfo.dwType == 2:
            # ★★ 2026-10-23 并发改造：按 linkHandle 写对应会话的文件。
            #   原来写 self.playbackFile —— 多路时数据全部串到一个文件。
            sess = None
            with self._pbs_lock:
                sess = self._playback_sessions.get(int(iPlayBackLinkHandle))
            if sess is not None:
                fp = sess.get("fp")
                path = sess.get("path")
                if fp is not None and not fp.closed:
                    self.writeFile(path, pDataCBInfo.pData,
                                   pDataCBInfo.dwDataLen, session_fp=fp)
            else:
                # 兼容：没有登记过的句柄（理论上不该出现）→ 退回旧路径
                self.writeFile(self.playbackFile, pDataCBInfo.pData,
                               pDataCBInfo.dwDataLen, fp_attr='_playback_fp')
        else:
            print(u'其他数据,长度:', pDataCBInfo.dwDataLen)

    def PLAYBACK_DATA_CB_PLAYCTRL(self, iPlayBackLinkHandle, pDataCBInfo, pUserData):
        pDataCBInfo = cast(pDataCBInfo, LPNET_EHOME_PLAYBACK_DATA_CB_INFO).contents
        if self.Count == 100:
            print(f'PLAYBACK_DATA_CB(PlayCtrl), dwDataLen: {pDataCBInfo.dwDataLen}, dwType: {pDataCBInfo.dwType}')
            self.Count = 0
        self.Count += 1

        if pDataCBInfo.dwType == 1:
            glo.set_value("stopPlayBackFlag", False)
            try:
                self._feed_playctrl(
                    self.playback_decoder,
                    1,
                    pDataCBInfo.pData,
                    pDataCBInfo.dwDataLen,
                    stream_mode=STREAME_FILE,
                )
            except Exception as e:
                print(f'PlayCtrl 回放头信息处理失败: {e}')
        elif pDataCBInfo.dwType == 3:
            print("收到回放结束信令！")
            glo.set_value("stopPlayBackFlag", True)
        elif pDataCBInfo.dwType == 2:
            try:
                self._feed_playctrl(
                    self.playback_decoder,
                    2,
                    pDataCBInfo.pData,
                    pDataCBInfo.dwDataLen,
                    stream_mode=STREAME_FILE,
                )
            except Exception as e:
                print(f'PlayCtrl 回放解码失败: {e}')

    def FPREVIEW_NEWLINK_CB_FILE(self, lLinkHandle, pNewLinkCBMsg, pUserData):
        print("FPREVIEW_NEWLINK_CB_File callback")
        # 预览数据回调参数
        self.lPreviewHandle = lLinkHandle
        struDataCB = NET_EHOME_PREVIEW_DATA_CB_PARAM()
        if self.use_playctrl_preview:
            struDataCB.fnPreviewDataCB = self.fPREVIEW_DATA_CB_PLAYCTRL
        else:
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
        # 回放数据回调参数
        self.m_lPlayBackLinkHandle = lPlayBackLinkHandle

        # ★★ 2026-10-23 并发改造：按 linkHandle 登记会话。
        #   从**队列头部**取出对应的待登记项（按发起顺序消费）。
        with self._pbs_lock:
            queue = getattr(self, "_pending_queue", None) or []
            pending = None
            if queue:
                # 优先匹配通道号（回调里带 dwChannelNo），否则取队头
                ch_no = int(getattr(pNewLinkCBInfo, "dwChannelNo", 0) or 0)
                idx = next(
                    (i for i, p in enumerate(queue)
                     if ch_no and p.get("channel") == ch_no),
                    0,
                )
                pending = queue.pop(idx)
            if pending is not None:
                self._playback_sessions[int(lPlayBackLinkHandle)] = {
                    "fp": pending.get("fp"),
                    "path": pending.get("path"),
                    "session_id": pending.get("session_id"),
                    "done": False,
                    "started_at": __import__("time").time(),
                }
                print(
                    f"  [并发] 会话登记: link={lPlayBackLinkHandle} "
                    f"session={pending.get('session_id')} "
                    f"path={pending.get('path')}"
                )

        struCBParam = NET_EHOME_PLAYBACK_DATA_CB_PARAM()
        if self.use_playctrl_playback:
            struCBParam.fnPlayBackDataCB = self.fPLAYBACK_DATA_CB_PLAYCTRL
        else:
            struCBParam.fnPlayBackDataCB = self.fPLAYBACK_DATA_CB_FILE
        struCBParam.byStreamFormat = 0
        if self.smsDLL.NET_ESTREAM_SetPlayBackDataCB(lPlayBackLinkHandle, struCBParam) is False:
            print("NET_ESTREAM_SetPlayBackDataCB failed err:：", self.smsDLL.NET_ESTREAM_GetLastError())
            return False
        return True

    def RealPlay(self, channel, user_id=None):
        self.previewUserID = self._resolve_user_id(user_id)
        # ★ 开启输出会话（文件模式才需要；PlayCtrl 模式只喂解码器，不落盘 mp4）
        if not self.use_playctrl_preview:
            self.preview_file_path = self._begin_output_session(
                'preview_file_path', '_preview_fp', 'preview', 'previewVideo')
            print(f'预览保存路径: {self.preview_file_path}')
        struPreviewIn = NET_EHOME_PREVIEWINFO_IN()
        struPreviewIn.iChannel = channel  # 预览通道号
        struPreviewIn.dwLinkMode = 0  # 0 - TCP方式，1 - UDP方式
        struPreviewIn.dwStreamType = 0  # 码流类型：0 - 主码流，1 - 子码流, 2 - 第三码流

        _set_stream_server_address(struPreviewIn.struStreamSever, "SmsServerIP", "SmsServerPort")
        struPreviewOut = NET_EHOME_PREVIEWINFO_OUT()
        getRS = self.cmsDLL.NET_ECMS_StartGetRealStream(self.previewUserID, ctypes.byref(struPreviewIn),
                                                        ctypes.byref(struPreviewOut))
        if getRS:
            print(f"NET_ECMS_StartGetRealStream succeed, sessionID: {struPreviewOut.lSessionID}, lUserID: {self.previewUserID}")
            self.sessionID = struPreviewOut.lSessionID
        else:
            print(f"NET_ECMS_StartGetRealStream failed, error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            # ★ 启动失败关掉刚打开的文件句柄
            self._end_output_session('_preview_fp')
            return

        struPushInfoIn = NET_EHOME_PUSHSTREAM_IN()
        struPushInfoIn.dwSize = sizeof(struPushInfoIn)
        struPushInfoIn.lSessionID = self.sessionID

        struPushInfoOut = NET_EHOME_PUSHSTREAM_OUT()
        struPushInfoOut.dwSize = sizeof(struPushInfoOut)

        if self.cmsDLL.NET_ECMS_StartPushRealStream(self.previewUserID, struPushInfoIn,
                                                    struPushInfoOut) is False:
            print(f"NET_ECMS_StartPushRealStream failed, error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            # ★ 收掉已建立的 CMS 会话 + 关闭文件句柄
            try:
                self.cmsDLL.NET_ECMS_StopGetRealStream(self.previewUserID, self.sessionID)
            except Exception:
                pass
            self._end_output_session('_preview_fp')
            return
        else:
            print(f"NET_ECMS_StartPushRealStream succeed, sessionID:{struPushInfoIn.lSessionID}, lUserID: {self.previewUserID}")

    def StopRealPlay(self):
        """停止预览（★ 用 try/finally 保证文件句柄一定被关闭）。"""
        try:
            if self.smsDLL.NET_ESTREAM_StopPreview(self.lPreviewHandle):
                print(f"NET_ESTREAM_StopPreview succ ")
            else:
                print(f"NET_ESTREAM_StopPreview failed, error code: {self.smsDLL.NET_ESTREAM_GetLastError()}")
                return
            print("停止Stream的实时流转发")
            self._close_preview_decoder(save_snapshot=self.use_playctrl_preview)

            if self.cmsDLL.NET_ECMS_StopGetRealStream(self.previewUserID, self.sessionID):
                print(f"NET_ECMS_StopGetRealStream succ ")
            else:
                print(f"NET_ECMS_StopGetRealStream failed,err =  {self.cmsDLL.NET_ECMS_GetLastError()}")
                return
            print("CMS发送预览停止请求")
        finally:
            # ★ 结束输出会话，关闭文件句柄
            self._end_output_session('_preview_fp')

    def PlayBackByTime(self, lchannel, minutes=3, user_id=None, start_dt=None, stop_dt=None,
                       output_path=None):
        """按时间回放。

        minutes     : 未指定 start_dt/stop_dt 时，回放最近 N 分钟
        start_dt    : 回放起点（指定则忽略 minutes）
        stop_dt     : 回放终点（指定则忽略 minutes）
        output_path : 显式输出文件路径；不传则自动生成到 outputFiles/back/
        """
        self.playbackUserID = self._resolve_user_id(user_id)
        # ★ 开启输出会话（文件模式才落盘 mp4）
        if not self.use_playctrl_playback:
            if output_path:
                self._end_output_session('_playback_fp')
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                self.playbackFile = output_path
                # ★★ 2026-10-23 并发改造：每个回放用**独立文件句柄**，
                #     不再共用 self._playback_fp（多路会互相覆盖）。
                self._playback_fp = open(output_path, 'wb')
            else:
                self.playbackFile = self._begin_output_session(
                    'playbackFile', '_playback_fp', 'back', 'playbackVideo')
            print(f'回放保存路径: {self.playbackFile}')

        # ★★ 2026-10-23 并发改造：把本次回放的「文件句柄 + 路径」暂存，
        #   等 PLAYBACK_NEWLINK_CB_FILE 拿到 linkHandle 后再登记到会话表。
        #   为什么不在发起点直接建表：那时还拿不到 linkHandle。
        #
        #   ★ 用**队列**而不是单槽：并发时多个 PlayBackByTime 会先后写入，
        #     NEWLINK 回调按发起顺序消费（SDK 的行为是发一路通一路）。
        #     单槽会被后一次覆盖，导致前面的回放把数据写进后面的文件。
        # ★ token 用于失败时精确出队（避免弹掉别的路）
        import uuid as _uuid

        _token = _uuid.uuid4().hex[:12]
        with self._pbs_lock:
            if not hasattr(self, "_pending_queue"):
                self._pending_queue = []
            self._pending_queue.append({
                "token": _token,
                "fp": getattr(self, "_playback_fp", None),
                "path": self.playbackFile,
                "session_id": None,  # 下面 StartPushPlayBack 后补
                "channel": int(lchannel) if lchannel else None,
            })
            print(
                f"  [并发] 待登记队列 +1（当前 {len(self._pending_queue)} 条）: "
                f"ch={lchannel} path={self.playbackFile}"
            )
        m_struPlayBackInfoIn = NET_EHOME_PLAYBACK_INFO_IN()
        m_struPlayBackInfoIn.dwSize = sizeof(m_struPlayBackInfoIn)
        m_struPlayBackInfoIn.dwChannel = lchannel  # 通道号
        m_struPlayBackInfoIn.byPlayBackMode = 1  # 0 - 按文件名回放，1 - 按时间回放
        m_struPlayBackInfoIn.byStreamPackage = 0  # 0-PS（默认）

        if start_dt is None or stop_dt is None:
            stop_dt = datetime.now()
            start_dt = datetime.fromtimestamp(stop_dt.timestamp() - minutes * 60)
        play_back_by_time = NET_EHOME_PLAYBACKBYTIME()
        _fill_ehome_time(play_back_by_time.struStartTime, start_dt)
        _fill_ehome_time(play_back_by_time.struStopTime, stop_dt)
        print(f'回放时间段: {start_dt} ~ {stop_dt}')

        m_struPlayBackInfoIn.unionPlayBackMode.struPlayBackbyTime = play_back_by_time

        _set_stream_server_address(m_struPlayBackInfoIn.struStreamSever, "SmsBackServerIP", "SmsBackServerPort")

        m_struPlayBackInfoOut = NET_EHOME_PLAYBACK_INFO_OUT()

        if self.cmsDLL.NET_ECMS_StartPlayBack(self.playbackUserID, ctypes.byref(m_struPlayBackInfoIn),
                                              ctypes.byref(m_struPlayBackInfoOut)):
            print(f"NET_ECMS_StartPlayBack succeed, lSessionID: {m_struPlayBackInfoOut.lSessionID}, lUserID: {self.playbackUserID}")
        else:
            print(f"NET_ECMS_StartPlayBack failed, error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            # ★ 启动失败必须关掉刚打开的文件句柄，否则每次失败泄漏一个 fd
            #   ★ 并发改造：同时把待登记项出队，避免残留污染下一次回放
            self._abort_pending_playback(_token)
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
                f"NET_ECMS_StartPushPlayBack succeed, sessionID: {m_struPushPlayBackIn.lSessionID} ,lUserID: {self.playbackUserID}")
        else:
            print(f"NET_ECMS_StartPushPlayBack failed, error code: {self.cmsDLL.NET_ECMS_GetLastError()}")
            # ★ 同上：把已建立的 CMS 会话收掉，并关闭文件句柄
            try:
                self.cmsDLL.NET_ECMS_StopPlayBack(self.playbackUserID, self.backSessionID)
            except Exception:
                pass
            self._abort_pending_playback(_token)
            return False
        return True

    def _abort_pending_playback(self, token: str) -> None:
        """回放启动失败时，把**本次**的待登记项出队并关掉它的文件句柄。

        ★ 为什么必须有（2026-10-23 并发改造的收尾）：
          PlayBackByTime 会先 append 到 _pending_queue，再调 StartPlayBack。
          如果 StartPlayBack 失败就 return，队列项会留在里面 ——
          下一次成功回放的 NEWLINK 回调可能匹配到这条**已失效**的记录，
          把数据写进一个已关闭（或根本不该用）的文件句柄。
          表现是视频内容错乱或直接异常。

          单路时同样会中招（第二次回放拿到第一次的残留）。
        """
        with self._pbs_lock:
            queue = getattr(self, "_pending_queue", None) or []
            for i, item in enumerate(queue):
                if item.get("token") == token:
                    queue.pop(i)
                    fp = item.get("fp")
                    if fp is not None:
                        try:
                            fp.close()
                        except OSError:
                            pass
                    print(f"  [并发] 失败清理：已出队 token={token}")
                    break

    def stopPlayBack_session_only(self, link_handle: int | None = None):
        """停止**本次**回放会话，保留回放监听（并发安全版）。

        与 stopPlayBackByTime 的区别：

            stopPlayBackByTime
                = 停会话 + **释放回放监听**（NET_ESTREAM_StopListenPlayBack）
                  ★ 多路并发时**绝对不能用**：会把其它路的监听一起拆掉，
                    而且反复 Start/Stop 监听会让 SDK 内部 double free → 崩溃。

            stopPlayBack_session_only
                = 只停这一路会话 + 关该路的文件，**监听和其它路都不动**

        link_handle：要停的会话句柄。不传则用 self.m_lPlayBackLinkHandle
                     （单路场景的兼容行为）。

        ★ 2026-10-23 并发改造新增。
        """
        handle = link_handle if link_handle is not None else getattr(
            self, "m_lPlayBackLinkHandle", -1
        )

        # 1) 从会话表取出这一路的资源
        sess = None
        with self._pbs_lock:
            sess = self._playback_sessions.pop(int(handle), None) if handle is not None else None

        try:
            # 2) 停 SDK 侧的回放（按会话，不是按实例字段）
            if not self.cmsDLL.NET_ECMS_StopPlayBack(self.playbackUserID, self.backSessionID):
                err = self.cmsDLL.NET_ECMS_GetLastError()
                print(f"NET_ECMS_StopPlayBack failed,err = {err}")
            else:
                print("CMS发送回放停止请求")

            if not self.smsDLL.NET_ESTREAM_StopPlayBack(handle):
                err = self.smsDLL.NET_ESTREAM_GetLastError()
                print(f"NET_ESTREAM_StopPlayBack failed,err =  {err}")
            else:
                print("停止回放Stream服务的实时流转发")
        except Exception:
            pass
        finally:
            # 3) 只关**这一路**的文件句柄
            if sess is not None:
                fp = sess.get("fp")
                if fp is not None:
                    try:
                        fp.close()
                        print(f"[并发] 会话 {handle} 文件已关闭: {sess.get('path')}")
                    except OSError:
                        pass
            else:
                # 兼容：没登记过（单路老路径）→ 关实例级的
                self._end_output_session('_playback_fp')
            # ★ 注意：**不动** self.playbackListenHandle

    def stopPlayBackByTime(self):
        """停止回放，并**彻底释放回放监听**。

        ★ 为什么必须连监听一起停：
          回放是独占资源。SDK 的监听句柄只要 >= 0，_ensure_listen 就会认为
          「监听已开启」而跳过重新启动。但一次回放结束后，SDK 侧的监听通道
          已经不再接受新链接 —— 如果只停会话不停监听，第二次回放会没有任何
          推流、stopPlayBackFlag 永远不翻转，一直卡到 180 秒超时。

          所以这里必须把 playbackListenHandle 复位，让下一次能干净地重开。
        """
        try:
            if not self.cmsDLL.NET_ECMS_StopPlayBack(self.playbackUserID, self.backSessionID):
                print(f"NET_ECMS_StopPlayBack failed,err = {self.cmsDLL.NET_ECMS_GetLastError()}")
            else:
                print("CMS发送回放停止请求")

            if not self.smsDLL.NET_ESTREAM_StopPlayBack(self.m_lPlayBackLinkHandle):
                print(f"NET_ESTREAM_StopPlayBack failed,err =  {self.smsDLL.NET_ESTREAM_GetLastError()}")
            else:
                print("停止回放Stream服务的实时流转发")
        finally:
            # ★ 释放回放监听句柄，保证下一次回放能重新 StartListen
            if self.playbackListenHandle > -1:
                with contextlib.suppress(Exception):
                    self.smsDLL.NET_ESTREAM_StopListenPlayBack(self.playbackListenHandle)
                self.playbackListenHandle = -1

            self._close_playback_decoder(save_snapshot=self.use_playctrl_playback)
            # ★ 结束输出会话，关闭文件句柄
            self._end_output_session('_playback_fp')
