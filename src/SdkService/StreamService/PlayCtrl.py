# -*- coding: utf-8 -*-
import os
from ctypes import *

from src.SdkService.CmsService.HCISUPCMS import target_dir, load_library, sys_platform

STREAME_REALTIME = 0
STREAME_FILE = 1

# ★ Linux 修复：原代码写死 PlayCtrl.dll，Linux 上对应的是 libPlayCtrl.so。
#   注意：V2.5.1.35 Linux64 包里不带 libPlayCtrl.so（需单独的 playctrl_linux 包），
#   缺它只影响 PlayCtrl 解密解码模式；服务器走 _FILE 模式（原始码流写文件），
#   不实例化本类，因此缺失不影响主流程。
if sys_platform == 'linux':
    playctrl_dllpath = os.path.join(target_dir, 'lib', 'libPlayCtrl.so')
else:
    playctrl_dllpath = os.path.join(target_dir, 'lib', 'PlayCtrl.dll')


def playctrl_available() -> bool:
    """PlayCtrl 解码库是否就位。缺它只影响带解密的取流快照，不影响主流程。"""
    return os.path.exists(playctrl_dllpath)


class PlayCtrlDecoder(object):
    """PlayCtrl 解码器：用于 ISUP 加密码流解密与解码（无窗口）。"""

    def __init__(self):
        self.dll = load_library(playctrl_dllpath)
        self.port = c_long(-1)
        self.started = False
        self._bind_functions()

    def _bind_functions(self):
        self.dll.PlayM4_GetPort.argtypes = [POINTER(c_long)]
        self.dll.PlayM4_GetPort.restype = c_bool

        self.dll.PlayM4_FreePort.argtypes = [c_long]
        self.dll.PlayM4_FreePort.restype = c_bool

        self.dll.PlayM4_SetStreamOpenMode.argtypes = [c_long, c_ulong]
        self.dll.PlayM4_SetStreamOpenMode.restype = c_bool

        self.dll.PlayM4_OpenStream.argtypes = [c_long, c_char_p, c_ulong, c_ulong]
        self.dll.PlayM4_OpenStream.restype = c_bool

        self.dll.PlayM4_InputData.argtypes = [c_long, c_char_p, c_ulong]
        self.dll.PlayM4_InputData.restype = c_bool

        self.dll.PlayM4_Play.argtypes = [c_long, c_void_p]
        self.dll.PlayM4_Play.restype = c_bool

        self.dll.PlayM4_Stop.argtypes = [c_long]
        self.dll.PlayM4_Stop.restype = c_bool

        self.dll.PlayM4_CloseStream.argtypes = [c_long]
        self.dll.PlayM4_CloseStream.restype = c_bool

        self.dll.PlayM4_SetDisplayBuf.argtypes = [c_long, c_ulong]
        self.dll.PlayM4_SetDisplayBuf.restype = c_bool

        self.dll.PlayM4_GetLastError.argtypes = [c_long]
        self.dll.PlayM4_GetLastError.restype = c_ulong

        self.dll.PlayM4_GetJPEG.argtypes = [c_long, c_char_p, c_ulong, POINTER(c_ulong)]
        self.dll.PlayM4_GetJPEG.restype = c_bool

    def _last_error(self):
        if self.port.value < 0:
            return -1
        return self.dll.PlayM4_GetLastError(self.port.value)

    def open_header(self, data, stream_mode=STREAME_REALTIME):
        if self.started:
            return True

        if not self.dll.PlayM4_GetPort(byref(self.port)):
            raise RuntimeError(f'PlayM4_GetPort failed, err={self._last_error()}')

        if not self.dll.PlayM4_SetStreamOpenMode(self.port.value, stream_mode):
            raise RuntimeError(f'PlayM4_SetStreamOpenMode failed, err={self._last_error()}')

        header = create_string_buffer(data, len(data))
        if not self.dll.PlayM4_OpenStream(self.port.value, header, len(data), 2 * 1024 * 1024):
            raise RuntimeError(f'PlayM4_OpenStream failed, err={self._last_error()}')

        self.dll.PlayM4_SetDisplayBuf(self.port.value, 6)

        # hWnd=0：无预览窗口，仅解码（含解密）
        if not self.dll.PlayM4_Play(self.port.value, None):
            raise RuntimeError(f'PlayM4_Play failed, err={self._last_error()}')

        self.started = True
        print(f'PlayCtrl 解码已启动, port={self.port.value}, header={len(data)} bytes')
        return True

    def input_data(self, data):
        if not self.started:
            return False
        buf = create_string_buffer(data, len(data))
        return bool(self.dll.PlayM4_InputData(self.port.value, buf, len(data)))

    def save_jpeg(self, file_path):
        if not self.started:
            return False

        jpeg_size = c_ulong(0)
        buf_size = 2 * 1024 * 1024
        jpeg_buf = create_string_buffer(buf_size)

        if not self.dll.PlayM4_GetJPEG(self.port.value, jpeg_buf, buf_size, byref(jpeg_size)):
            print(f'PlayM4_GetJPEG failed, err={self._last_error()}')
            return False

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(jpeg_buf.raw[:jpeg_size.value])
        print(f'PlayCtrl 解码快照已保存: {file_path}')
        return True

    def close(self):
        if self.port.value < 0:
            return

        if self.started:
            self.dll.PlayM4_Stop(self.port.value)
            self.dll.PlayM4_CloseStream(self.port.value)
            self.started = False

        self.dll.PlayM4_FreePort(self.port.value)
        print(f'PlayCtrl 解码已停止, port={self.port.value}')
        self.port = c_long(-1)
