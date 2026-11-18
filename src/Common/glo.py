# -*- coding: utf-8 -*-
# @Time : 2023/9/13 12:36
# @Author : qiu jiahang

'''用于保存全局共享字段'''


def _init():  # 初始化
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    # 定义一个全局变量
    _global_dict[key] = value


def get_value(key, defValue=None):
    # 获得全局变量，不存在则返回默认值
    try:
        return _global_dict[key]
    except KeyError:
        return defValue


# ---------------------------------------------------------------------------
# 多设备登录句柄管理（合并自同事 XY-development 版本）
#
# 背景：原实现每来一台设备就 glo.set_value('iUserID', lUserID) 直接覆盖，
#       而取流/回放全程读这个全局值 —— 多设备同时在线时，预览/回放会打到
#       **最后上线的那台设备**上。这里改成 设备ID ↔ iUserID 双映射表。
# ---------------------------------------------------------------------------
def init_runtime_state():
    """初始化运行期设备状态。必须在 loadJsonConfToGlobal 里调用。"""
    set_value('iUserID', -1)
    set_value('deviceUserMap', {})
    set_value('userDeviceMap', {})


def register_device(device_id, user_id):
    """设备上线：登记双向映射，并把 iUserID 指向该设备。"""
    device_map = get_value('deviceUserMap', {})
    user_map = get_value('userDeviceMap', {})
    device_map[device_id] = user_id
    user_map[user_id] = device_id
    set_value('deviceUserMap', device_map)
    set_value('userDeviceMap', user_map)
    set_value('iUserID', user_id)


def unregister_device(user_id):
    """设备离线：摘掉映射。若还有其他设备在线，iUserID 回退到其中一台。"""
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
    """返回 {device_id: iUserID} 的快照。"""
    return dict(get_value('deviceUserMap', {}))


def resolve_device_user_id(config_key, action_label, interactive=True):
    """解析本次操作该用哪个登录句柄。

    优先级：配置指定的设备 > 唯一在线设备 > 交互式选择。
    找不到时返回 None（调用方需处理）。
    """
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
