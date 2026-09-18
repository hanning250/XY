# -*- coding: utf-8 -*-
"""一次性运行：最近 1 分钟回放（f3004）"""
import sys

from src.Common import glo
from src.Common.DemoRuntime import start_all_services, stop_all_services
from src.DemoApp.SDKFunctionDemo import run_playback_by_time

WAIT_TIMEOUT = 120


def main():
    ams, ss, cms, sms = start_all_services(run_cleanup=True)

    if not glo.wait_for_device(timeout=WAIT_TIMEOUT):
        print('超时：设备未注册上线')
        stop_all_services(sms, cms, ams, ss)
        sys.exit(1)

    print('开始回放最近 1 分钟...')
    if not run_playback_by_time(sms, interactive=False, channel=1, minutes=1):
        stop_all_services(sms, cms, ams, ss)
        sys.exit(1)

    stop_all_services(sms, cms, ams, ss)


if __name__ == '__main__':
    main()
