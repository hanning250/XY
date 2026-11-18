# -*- coding: utf-8 -*-
# @Time : 2023/9/11 20:45
# @Author : qiu jiahang
import os
from ctypes import CFUNCTYPE, c_bool, c_int16, c_int, c_char_p, POINTER, c_void_p, string_at, memmove, sizeof, c_uint32, \
    c_long, c_byte


# @CFUNCTYPE(c_bool, c_int16, c_int, POINTER(c_void_p), c_uint32, POINTER(c_void_p), c_uint32,
#            POINTER(c_void_p))
from src.SdkService.CmsService.HCISUPCMS import target_dir, fun_ctype


@fun_ctype(c_bool, c_long, c_byte, POINTER(c_void_p), c_uint32, POINTER(c_char_p), c_uint32,
                               POINTER(c_void_p))
def pss_message_callback(iHandle, enumType, pOutBuffer, dwOutLen, pInBuffer, dwInLen, pUser):
    print('PSS_Message_Callback')
    return True


# 文件存储回调函数
# @CFUNCTYPE(c_bool, c_int16, POINTER(c_char_p), POINTER(c_void_p), c_uint32, POINTER(c_char_p),
#            POINTER(c_void_p))
@fun_ctype(c_bool, c_long, c_char_p, POINTER(c_void_p), c_uint32, POINTER(c_char_p),
                                  POINTER(c_void_p))
def pss_storage_callback(iHandle, pFileName, pFileBuf, dwFileLen, pFilePath, pUser):
    #存储服务存储路径
    # ★ Linux 修复：原代码用 target_dir + '\\storage'，在 Linux 上会得到
    #   形如 /app\storage 的非法路径（反斜杠是合法文件名字符，目录建不出来）。
    #   改用 os.path.join 自动适配分隔符，Windows/Linux 都正确。
    strPath = os.path.join(target_dir, 'storage')
    os.makedirs(strPath, exist_ok=True)
    file_name = string_at(pFileName).decode('UTF-8').strip()
    if not file_name.lower().endswith(('.jpg', '.jpeg')):
        file_name = file_name + '.jpg'
    file_path = os.path.join(strPath, file_name)

    with open(file_path, "wb") as f:
        f.write(string_at(pFileBuf, dwFileLen))
    print(f'告警图片已保存: {file_path}')
    s = c_char_p(file_path.encode('utf-8'))
    s_len = string_at(s).decode('UTF-8')
    memmove(pFilePath, s, s_len.__sizeof__())
    # print("sizeof(s): ", sizeof(s))
    # print(string_at(pFilePath).decode('UTF-8'))

    return True


@fun_ctype(c_bool, c_long, c_byte, c_char_p, POINTER(c_void_p), POINTER(c_long), c_char_p,
                              POINTER(c_void_p))
def pss_ssrw_callback(iHandle, byAct, pFileName, pFileBuf, dwFileLen, pFileUrl, pUser):
    print('pss_ssrw_callback')
    return True