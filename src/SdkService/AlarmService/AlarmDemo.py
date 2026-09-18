# -*- coding: utf-8 -*-
# @Time : 2023/9/8 10:57
# @Author : qiu jiahang
import ctypes
import json
import re
from ctypes import *

from src.Common import glo
from src.Common.ListenHelper import bind_ip_address
from src.Common.SdkInit import configure_com_path, configure_openssl, configure_sdk_log
from src.SdkService.AlarmService.HCISUPAlarm import NET_EHOME_ALARM_LISTEN_PARAM, NET_EHOME_ALARM_MSG, \
    LPNET_EHOME_ALARM_MSG, NET_EHOME_ALARM_ISAPI_INFO, LPNET_EHOME_ALARM_ISAPI_INFO, ams_sdkdllpath, \
    NET_EHOME_EALARM_INIT_CFG_TYPE
from src.SdkService.CmsService.HCISUPCMS import load_library, libeay_dllpath, ssleay_dllpath, strPathCom_dllpath, \
    NET_EHOME_LOCAL_CFG_TYPE, fun_ctype, target_dir

def _alarm_print_detail():
    return bool(glo.get_value('AlarmPrintDetail', True))


def _tag(text, name):
    match = re.search(rf'<{name}>([^<]*)</{name}>', text)
    return match.group(1) if match else ''


def _collect_alarm_texts(alarm_struct):
    texts = []
    if alarm_struct.dwXmlBufLen != 0:
        texts.append(str(
            ctypes.string_at(alarm_struct.pXmlBuf, alarm_struct.dwXmlBufLen),
            'UTF-8',
        ).rstrip('\x00'))
    if alarm_struct.dwAlarmType == 13 and alarm_struct.dwAlarmInfoLen > 0:
        isapi_info = ctypes.cast(alarm_struct.pAlarmInfo, LPNET_EHOME_ALARM_ISAPI_INFO).contents
        if isapi_info.dwAlarmDataLen != 0:
            texts.append(str(
                ctypes.string_at(isapi_info.pAlarmData, isapi_info.dwAlarmDataLen),
                'UTF-8',
            ).rstrip('\x00'))
    return [t for t in texts if t]


def _pick_event_xml(texts):
    for text in texts:
        if 'EventNotificationAlert' in text or '<deviceID>' in text:
            return text
    return texts[0] if texts else ''


def _extract_alarm_summary(event_xml, dw_type):
    device_id = _tag(event_xml, 'deviceID')
    event_type = _tag(event_xml, 'eventType') or f'type{dw_type}'
    event_state = _tag(event_xml, 'eventState')
    io_port = _tag(event_xml, 'inputIOPortID')
    date_time = _tag(event_xml, 'dateTime')
    channel_name = _tag(event_xml, 'channelName')

    parts = [f'[报警] {device_id or "?"}', event_type]
    if channel_name:
        parts.append(channel_name)
    if io_port:
        parts.append(f'IO{io_port}')
    if event_state:
        parts.append(event_state)
    if date_time:
        parts.append(date_time)
    return ' '.join(parts)


def _parse_alarm_event(i_handle, alarm_struct, texts, event_xml):
    """Normalize SDK alarm payload into a dict for backend persistence."""
    device_id = _tag(event_xml, 'deviceID')
    event_type = _tag(event_xml, 'eventType') or f'type{alarm_struct.dwAlarmType}'
    event_state = _tag(event_xml, 'eventState')
    io_port = _tag(event_xml, 'inputIOPortID')
    date_time = _tag(event_xml, 'dateTime')
    channel_name = _tag(event_xml, 'channelName')
    channel_id = _tag(event_xml, 'channelID')

    isapi_data_type = None
    pictures_number = None
    if alarm_struct.dwAlarmType == 13 and alarm_struct.dwAlarmInfoLen > 0:
        isapi_info = ctypes.cast(alarm_struct.pAlarmInfo, LPNET_EHOME_ALARM_ISAPI_INFO).contents
        isapi_data_type = isapi_info.byDataType
        pictures_number = isapi_info.byPicturesNumber

    raw_json = None
    raw_xml = event_xml or None
    for text in texts:
        stripped = text.strip()
        if stripped.startswith('{') or stripped.startswith('['):
            raw_json = stripped
        elif 'EventNotificationAlert' in text or '<deviceID>' in text:
            raw_xml = text

    if raw_json:
        try:
            payload = json.loads(raw_json)
            if isinstance(payload, dict):
                device_id = device_id or payload.get('deviceID') or payload.get('deviceId')
                date_time = date_time or payload.get('dateTime')
                event_type = payload.get('eventType') or event_type
                if not channel_id and payload.get('channelID') is not None:
                    channel_id = str(payload.get('channelID'))
        except json.JSONDecodeError:
            pass

    device_map = glo.get_value('deviceUserMap', {})
    cms_user_id = device_map.get(device_id) if device_id else None

    return {
        'handle': i_handle,
        'alarm_type': alarm_struct.dwAlarmType,
        'device_id': device_id or None,
        'event_type': event_type,
        'event_state': event_state or None,
        'io_port': io_port or None,
        'date_time': date_time or None,
        'channel_name': channel_name or None,
        'channel_id': channel_id or None,
        'isapi_data_type': isapi_data_type,
        'pictures_number': pictures_number,
        'raw_xml': raw_xml,
        'raw_json': raw_json,
        'cms_user_id': cms_user_id,
    }


def _dispatch_alarm_event(event_dict):
    handler = glo.get_value('alarm_event_handler')
    if handler:
        try:
            handler(event_dict)
        except Exception as exc:
            print(f'[报警] 后端分发失败: {exc}')


def _format_alarm_detail(alarm_struct, texts):
    lines = [
        f'AlarmType: {alarm_struct.dwAlarmType}',
        f'dwAlarmInfoLen: {alarm_struct.dwAlarmInfoLen}',
        f'dwXmlBufLen: {alarm_struct.dwXmlBufLen}',
    ]
    if alarm_struct.dwAlarmType == 13 and alarm_struct.dwAlarmInfoLen > 0:
        isapi_info = ctypes.cast(alarm_struct.pAlarmInfo, LPNET_EHOME_ALARM_ISAPI_INFO).contents
        lines.append(f'ISAPI byDataType: {isapi_info.byDataType}, byPicturesNumber: {isapi_info.byPicturesNumber}')

    for index, text in enumerate(texts, start=1):
        stripped = text.strip()
        if stripped.startswith('{') or stripped.startswith('['):
            try:
                stripped = json.dumps(json.loads(stripped), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
        lines.append(f'--- 报警内容 #{index} ---')
        lines.append(stripped)
    return '\n'.join(lines)


@fun_ctype(c_bool, c_long, POINTER(NET_EHOME_ALARM_MSG), POINTER(c_void_p))
def EHomeMsgCallBack(iHandle, pAlarmMsg, pUser):
    alarm_struct = ctypes.cast(pAlarmMsg, LPNET_EHOME_ALARM_MSG).contents
    dw_type = alarm_struct.dwAlarmType
    texts = _collect_alarm_texts(alarm_struct)
    event_xml = _pick_event_xml(texts)

    if _alarm_print_detail():
        print(_format_alarm_detail(alarm_struct, texts))
    elif event_xml:
        print(_extract_alarm_summary(event_xml, dw_type))
    else:
        print(f'[报警] type{dw_type} （未解析到事件XML）')

    _dispatch_alarm_event(_parse_alarm_event(iHandle, alarm_struct, texts, event_xml))

    return True


class amsClass(object):
    '''ams服务类'''

    def __init__(self):
        self.amsHandle = -1
        self.cbEHomeMsgCallBack = None
        self.amsDLL = self.loadDLL()
        glo.set_value('amsDLL', self.amsDLL)

    def loadDLL(self):
        try:
            print("ams_sdkdllpath: ", ams_sdkdllpath)
            self.amsDLL = load_library(ams_sdkdllpath)
            configure_openssl(
                self.amsDLL,
                self.amsDLL.NET_EALARM_SetSDKInitCfg,
                NET_EHOME_EALARM_INIT_CFG_TYPE.NET_EHOME_EALARM_INIT_CFG_LIBEAY_PATH.value,
                NET_EHOME_EALARM_INIT_CFG_TYPE.NET_EHOME_EALARM_INIT_CFG_SSLEAY_PATH.value,
            )
            self.amsDLL.NET_EALARM_Init()
            configure_com_path(self.amsDLL, self.amsDLL.NET_EALARM_SetSDKLocalCfg, NET_EHOME_LOCAL_CFG_TYPE.COM_PATH.value)
            configure_sdk_log(self.amsDLL, self.amsDLL.NET_EALARM_SetLogToFile)
            return self.amsDLL
        except OSError as e:
            print('ams 动态库加载失败', e)

    def startAmsListen(self):
        if self.cbEHomeMsgCallBack is None:
            self.cbEHomeMsgCallBack = EHomeMsgCallBack
        net_ehome_alarm_listen_param = NET_EHOME_ALARM_LISTEN_PARAM()
        bind_ip_address(net_ehome_alarm_listen_param.struAddress, "AlarmServerListenIP", "AlarmServerListenTCPPort")
        net_ehome_alarm_listen_param.fnMsgCb = self.cbEHomeMsgCallBack
        net_ehome_alarm_listen_param.byProtocolType = glo.get_value('AlarmServerType')
        self.amsHandle = self.amsDLL.NET_EALARM_StartListen(ctypes.byref(net_ehome_alarm_listen_param))
        if self.amsHandle < 0:
            print('NET_EALARM_StartListen failed, error code: ', self.amsDLL.NET_EALARM_GetLastError())
        else:
            detail = '详细内容' if _alarm_print_detail() else '单行摘要'
            print('报警服务器: ', str(net_ehome_alarm_listen_param.struAddress.szIP, encoding="utf-8").rstrip(
                '\x00') + '_' + str(net_ehome_alarm_listen_param.struAddress.wPort))
            print(f'报警打印: {detail}')

    def stopAmsListen(self):
        if self.amsHandle > -1:
            self.amsDLL.NET_EALARM_StopListen(self.amsHandle)
            self.amsDLL.NET_EALARM_Fini()
