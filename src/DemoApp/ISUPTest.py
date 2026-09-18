# -*- coding: utf-8 -*-
# @Time : 2023/9/13 9:38
# @Author : qiu jiahang
from src.Common import glo
from src.Common.DemoRuntime import start_all_services, stop_all_services
from src.DemoApp import SDKFunctionDemo


if __name__ == '__main__':
    ams, ss, cms, sms = start_all_services(run_cleanup=True)
    glo.wait_for_device()

    exit_program = False
    while not exit_program:
        print("请输入您想要执行的demo实例! （退出请输入yes）")
        command = input().strip().lower()
        try:
            if command == "yes":
                exit_program = True
                break

            elif command[0] == 'f':
                SDKFunctionDemo.dispatch(command, cms, ss, sms)
                print("\n[Module]通用的sdk服务实例代码")

            else:
                print("\n未知的指令操作!请重新输入!\n")
        except IndexError:
            print("command is empty or not initialized")

    stop_all_services(sms, cms, ams, ss)
