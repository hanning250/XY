# -*- coding: utf-8 -*-
"""Demo 服务启动与停止。"""
from src.Common.CleanupExpiredFiles import cleanup_expired_files
from src.Common.ConfRead import getConfJson, loadJsonConfToGlobal
from src.SdkService.AlarmService.AlarmDemo import amsClass
from src.SdkService.CmsService.CmsDemo import cmsClass
from src.SdkService.SsService.SsDemo import ssClass
from src.SdkService.StreamService.StreamDemo import smsClass


def start_all_services(run_cleanup=True):
    if run_cleanup:
        cleanup_expired_files()
    loadJsonConfToGlobal(getConfJson())

    ams = amsClass()
    ams.startAmsListen()
    ss = ssClass()
    ss.startSsListen()
    cms = cmsClass()
    cms.startCmsListen()
    sms = smsClass()
    return ams, ss, cms, sms


def stop_all_services(sms, cms, ams, ss):
    sms.stopSmsListen()
    cms.stopCmsListen()
    ams.stopAmsListen()
    ss.stopSsListen()
