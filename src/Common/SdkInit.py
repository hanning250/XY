# -*- coding: utf-8 -*-
"""ISUP SDK 公共初始化辅助。"""
import ctypes
from ctypes import POINTER, c_void_p

from src.SdkService.CmsService.HCISUPCMS import libeay_dllpath, ssleay_dllpath, strPathCom_dllpath, target_dir


def create_ssl_init_pointers():
    libeay32_p = ctypes.cast(ctypes.c_char_p(libeay_dllpath.encode()), POINTER(c_void_p))
    ssleay32_p = ctypes.cast(ctypes.c_char_p(ssleay_dllpath.encode()), POINTER(c_void_p))
    return libeay32_p, ssleay32_p


def configure_openssl(dll, set_sdk_init_cfg, libeay_cfg_type, ssl_cfg_type):
    libeay32_p, ssleay32_p = create_ssl_init_pointers()
    set_sdk_init_cfg(libeay_cfg_type, libeay32_p)
    set_sdk_init_cfg(ssl_cfg_type, ssleay32_p)


def configure_com_path(dll, set_local_cfg, com_path_cfg_type):
    str_path_com_p = ctypes.cast(ctypes.c_char_p(strPathCom_dllpath.encode()), POINTER(c_void_p))
    set_local_cfg(com_path_cfg_type, str_path_com_p)


def configure_sdk_log(dll, set_log_to_file):
    set_log_to_file(3, (target_dir + '/IsupSDKLog/').encode('utf-8'), False)
