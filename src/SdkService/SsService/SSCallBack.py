# -*- coding: utf-8 -*-
# @Time : 2023/9/11 20:45
# @Author : qiu jiahang
import os
import time
from ctypes import c_bool, c_char_p, POINTER, c_void_p, string_at, memmove, c_uint32, c_long, c_byte

from src.Common import glo
from src.SdkService.CmsService.HCISUPCMS import target_dir, fun_ctype

_pic_last_print = {}
_pic_suppressed = {}


def _pic_print_throttle_seconds():
    value = glo.get_value('SsPicSavePrintThrottleSeconds', 30)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 30


def _print_pic_saved(file_path):
    throttle_sec = _pic_print_throttle_seconds()
    if throttle_sec <= 0:
        print(f'告警图片已保存: {file_path}')
        return

    now = time.time()
    last_print = _pic_last_print.get('pic_save', 0)
    if now - last_print < throttle_sec:
        _pic_suppressed['pic_save'] = _pic_suppressed.get('pic_save', 0) + 1
        return

    suppressed = _pic_suppressed.pop('pic_save', 0)
    message = f'告警图片已保存: {file_path}'
    if suppressed:
        message = f'{message} （期间另有 {suppressed} 张图片已保存至 storage/）'
    print(message)
    _pic_last_print['pic_save'] = now


@fun_ctype(c_bool, c_long, c_byte, POINTER(c_void_p), c_uint32, POINTER(c_char_p), c_uint32,
           POINTER(c_void_p))
def pss_message_callback(iHandle, enumType, pOutBuffer, dwOutLen, pInBuffer, dwInLen, pUser):
    return True


@fun_ctype(c_bool, c_long, c_char_p, POINTER(c_void_p), c_uint32, POINTER(c_char_p),
           POINTER(c_void_p))
def pss_storage_callback(iHandle, pFileName, pFileBuf, dwFileLen, pFilePath, pUser):
    strPath = target_dir + '\\storage'
    os.makedirs(strPath, exist_ok=True)
    file_name = string_at(pFileName).decode('UTF-8').strip()
    if not file_name.lower().endswith(('.jpg', '.jpeg')):
        file_name = file_name + '.jpg'
    file_path = os.path.join(strPath, file_name)

    with open(file_path, "wb") as f:
        f.write(string_at(pFileBuf, dwFileLen))
    _print_pic_saved(file_path)

    try:
        from src.Backend.image_registry import attach_image_to_latest_alarm, register_storage_image

        register_storage_image(file_path)
        alarm_id = attach_image_to_latest_alarm(file_path)
        if alarm_id is not None:
            print(f'告警图片已关联: alarm_id={alarm_id}, file={file_path}')
    except Exception as exc:
        print(f'告警图片关联失败: {exc}')

    s = c_char_p(file_path.encode('utf-8'))
    s_len = string_at(s).decode('UTF-8')
    memmove(pFilePath, s, s_len.__sizeof__())
    return True


@fun_ctype(c_bool, c_long, c_byte, c_char_p, POINTER(c_void_p), POINTER(c_long), c_char_p,
           POINTER(c_void_p))
def pss_ssrw_callback(iHandle, byAct, pFileName, pFileBuf, dwFileLen, pFileUrl, pUser):
    return True
