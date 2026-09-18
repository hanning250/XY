# -*- coding: utf-8 -*-
# @Time : 2023/9/13 12:36
# @Author : qiu jiahang

'''用于保存全局共享字段'''

_global_dict = None


def _init():  # 初始化
    global _global_dict
    _global_dict = {}


def _ensure_init():
    global _global_dict
    if _global_dict is None:
        _init()


def set_value(key, value):
    # 定义一个全局变量
    _ensure_init()
    _global_dict[key] = value


def get_value(key, defValue=None):
    # 获得全局变量，不存在则返回默认值
    _ensure_init()
    try:
        return _global_dict[key]
    except KeyError:
        return defValue


def init_runtime_state():
    set_value('iUserID', -1)
    set_value('deviceUserMap', {})
    set_value('userDeviceMap', {})


def register_device(device_id, user_id):
    device_map = get_value('deviceUserMap', {})
    user_map = get_value('userDeviceMap', {})
    device_map[device_id] = user_id
    user_map[user_id] = device_id
    set_value('deviceUserMap', device_map)
    set_value('userDeviceMap', user_map)
    set_value('iUserID', user_id)


def unregister_device(user_id):
    user_map = get_value('userDeviceMap', {})
    device_map = get_value('deviceUserMap', {})
    device_id = user_map.pop(user_id, None)
    if device_id:
        device_map.pop(device_id, None)
    set_value('userDeviceMap', user_map)
    set_value('deviceUserMap', device_map)
    if device_map:
        set_value('iUserID', next(iter(device_map.values())))
    else:
        set_value('iUserID', -1)


def list_online_devices():
    return dict(get_value('deviceUserMap', {}))


def get_active_user_id():
    """当前 CMS 默认登录句柄（与历史 iUserID 行为一致）。"""
    return get_value('iUserID')


def resolve_cms_user_id():
    """CMS 命令使用的登录句柄；未配置 CmsDeviceID 时与历史 iUserID 行为一致。"""
    devices = list_online_devices()
    preferred = get_value('CmsDeviceID', '')
    if preferred and preferred in devices:
        return devices[preferred]
    return get_active_user_id()


def wait_for_device(timeout=None):
    import time

    start = time.time()
    while get_value('iUserID') < 0:
        if timeout is not None and time.time() - start > timeout:
            return False
        print('等待设备注册上线！ iUserID：', get_value('iUserID'))
        time.sleep(1)
    return True


def resolve_device_user_id(config_key, action_label, interactive=True):
    devices = list_online_devices()
    if not devices:
        print(f"无在线设备，无法{action_label}")
        return None

    preferred = get_value(config_key)
    if preferred and preferred in devices:
        user_id = devices[preferred]
        print(f"使用配置设备: {preferred} (iUserID={user_id})")
        return user_id

    if len(devices) == 1:
        device_id, user_id = next(iter(devices.items()))
        print(f"使用唯一在线设备: {device_id} (iUserID={user_id})")
        return user_id

    print("当前在线设备:")
    for device_id, user_id in devices.items():
        print(f"  {device_id} -> iUserID={user_id}")

    if not interactive:
        print(f"未配置 {config_key} 且存在多设备，无法自动{action_label}")
        return None

    choice = input(f"请输入要{action_label}的设备ID: ").strip()
    if choice in devices:
        print(f"已选择设备: {choice} (iUserID={devices[choice]})")
        return devices[choice]
    print(f"未知设备ID: {choice}")
    return None
