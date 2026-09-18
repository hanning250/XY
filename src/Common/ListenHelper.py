# -*- coding: utf-8 -*-
"""监听地址绑定辅助。"""
import ctypes

from src.Common import glo


def bind_ip_address(ip_address_struct, ip_key, port_key):
    address = ctypes.create_string_buffer(glo.get_value(ip_key).encode())
    ctypes.memmove(ip_address_struct.szIP, address, ctypes.sizeof(address))
    ip_address_struct.wPort = glo.get_value(port_key)
