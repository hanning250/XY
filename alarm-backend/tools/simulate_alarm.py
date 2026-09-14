# -*- coding: utf-8 -*-
"""模拟器：不发真实报警，直接往服务里灌一条假告警，验证软件链路。

用途：在还没接盒子、或想确认「报警进来后能不能正确存图/入库/返回接口」时使用。
它**不经过 SDK 回调**，而是直接调 ISUPAlarmService 的处理逻辑，
等价于设备真的推了一条 ISAPI 报警过来。

用法（另开一个终端，先让服务跑起来）：
    uv run python tools/simulate_alarm.py --start      # 起一个带模拟接口的服务
    uv run python tools/simulate_alarm.py              # 往已运行的服务灌一条

常用参数：
    --count 3            连续灌 3 条
    --interval 2         每条间隔 2 秒
    --type vest          事件类型：vest(未穿反光衣) / helmet(未戴安全帽) / both
    --no-picture         不带图片（测「只有 JSON」的情况）
    --port 18080         指定服务端口
    --base http://...    直接指定服务地址
"""

import argparse
import json
import os
import sys
import threading
import time
from ctypes import (
    POINTER,
    addressof,
    c_byte,
    c_void_p,
    cast,
    create_string_buffer,
    memmove,
    sizeof,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.hcisup import (  # noqa: E402
    EHOME_ISAPI_ALARM,
    NET_EHOME_ALARM_ISAPI_INFO,
    NET_EHOME_ALARM_ISAPI_PICDATA,
    NET_EHOME_ALARM_MSG,
)

# 一张最小可用的 JPEG（1x1 灰点）。要更真实的图可换成真照片。
TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000"
    "ffdb004300ffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffff"
    "ffc0000b080001000101011100"
    "ffc40014000100000000000000000000000000000009"
    "ffda0008010100003f00d2cf20ffd9"
)

# 三种事件对应的 AIOP JSON + 中文标签
EVENT_PRESETS = {
    "vest": {
        "label": "未穿反光衣",
        "type": 0,
        "payload": {
            "width": "704",
            "height": "576",
            "targets": [
                {
                    "obj": {
                        "modelID": "sim-model",
                        "id": 1,
                        "type": 0,
                        "confidence": 936,
                        "valid": 1,
                        "visible": 1,
                        "rect": {
                            "x": "0.217483",
                            "y": "0.588785",
                            "w": "0.149191",
                            "h": "0.409346",
                        },
                    },
                    "properties": [
                        {
                            "classify": {
                                "attrType": 1,
                                "attrValue": 1,
                                "attrConf": 900,
                            }
                        }
                    ],
                }
            ],
            "events": {"alertInfo": [{"ruleInfo": {"ruleID": 3}}]},
        },
    },
    "helmet": {
        "label": "未戴安全帽",
        "type": 1,
        "payload": {
            "width": "704",
            "height": "576",
            "targets": [
                {
                    "obj": {
                        "modelID": "sim-model",
                        "id": 1,
                        "type": 1,
                        "confidence": 881,
                        "valid": 1,
                        "visible": 1,
                        "rect": {
                            "x": "0.31",
                            "y": "0.12",
                            "w": "0.11",
                            "h": "0.15",
                        },
                    }
                }
            ],
            "events": {"alertInfo": [{"ruleInfo": {"ruleID": 5}}]},
        },
    },
    "both": {
        "label": "未穿反光衣+未戴安全帽",
        "type": 0,
        "payload": {
            "width": "704",
            "height": "576",
            "targets": [
                {
                    "obj": {
                        "id": 1,
                        "type": 0,
                        "confidence": 936,
                        "valid": 1,
                        "visible": 1,
                        "rect": {"x": "0.21", "y": "0.58", "w": "0.14", "h": "0.40"},
                    }
                },
                {
                    "obj": {
                        "id": 2,
                        "type": 1,
                        "confidence": 812,
                        "valid": 1,
                        "visible": 1,
                        "rect": {"x": "0.31", "y": "0.12", "w": "0.11", "h": "0.15"},
                    }
                },
            ],
        },
    },
}


def set_field(struct_obj, field_name, data):
    """给 ctypes 结构体的定长数组字段赋值（c_char*N 取到的是 bytes 副本，要用偏移写）。"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    field = getattr(type(struct_obj), field_name)
    addr = addressof(struct_obj) + field.offset
    memmove(addr, data[: field.size], min(len(data), field.size))


class FakeAlarm:
    """按 SDK 内存布局拼一块 [MSG][ISAPI_INFO][JSON][PICDATA[]][JPEG...] 缓冲。"""

    def __init__(self, payload, pictures, serial=b"SIMBOX000001"):
        self.json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.pictures = list(pictures)

        isapi_size = sizeof(NET_EHOME_ALARM_ISAPI_INFO)
        pic_size = sizeof(NET_EHOME_ALARM_ISAPI_PICDATA)
        count = len(self.pictures)

        total = (
            sizeof(NET_EHOME_ALARM_MSG)
            + isapi_size
            + len(self.json_bytes)
            + pic_size * max(count, 1)
            + sum(len(p) for p in self.pictures)
        )
        self.buf = create_string_buffer(total)
        base = addressof(self.buf)

        self.msg = cast(self.buf, POINTER(NET_EHOME_ALARM_MSG)).contents
        self.msg.dwAlarmType = EHOME_ISAPI_ALARM
        set_field(self.msg, "sSerialNumber", serial)
        self.msg.pAlarmInfo = base + sizeof(NET_EHOME_ALARM_MSG)
        self.msg.dwAlarmInfoLen = isapi_size

        isapi_addr = base + sizeof(NET_EHOME_ALARM_MSG)
        isapi = cast(
            c_void_p(isapi_addr), POINTER(NET_EHOME_ALARM_ISAPI_INFO)
        ).contents
        isapi.byDataType = 2
        isapi.byPicturesNumber = count

        cursor = isapi_addr + isapi_size
        memmove(cursor, self.json_bytes, len(self.json_bytes))
        isapi.pAlarmData = cursor
        isapi.dwAlarmDataLen = len(self.json_bytes)
        cursor += len(self.json_bytes)

        if count:
            isapi.pPicPackData = cursor
            data_cursor = cursor + pic_size * count
            for index, data in enumerate(self.pictures):
                item_addr = cursor + pic_size * index
                item = cast(
                    c_void_p(item_addr), POINTER(NET_EHOME_ALARM_ISAPI_PICDATA)
                ).contents
                item.dwPicLen = len(data)
                set_field(item, "szFilename", f"sim_{index}.jpg")
                item.pPicData = cast(c_void_p(data_cursor), POINTER(c_byte))
                memmove(data_cursor, data, len(data))
                data_cursor += len(data)
        else:
            isapi.pPicPackData = None

    def pointer(self):
        return cast(self.buf, POINTER(NET_EHOME_ALARM_MSG))


def run_server_with_sim(port):
    """起一个和正式服务完全一样的服务，额外加一个 /simulate 注入接口。"""
    import uvicorn

    from core.alarm_service import ISUPAlarmService
    from common.storage import AlarmStorage
    from web.api import create_app
    from web.notifier import AlarmNotifier

    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, "r", encoding="utf-8") as fp:
        config = json.load(fp)

    storage = AlarmStorage(
        os.path.join(BASE_DIR, config["storage"]["db_path"]),
        os.path.join(BASE_DIR, config["storage"]["picture_dir"]),
    )
    notifier = AlarmNotifier()
    service = ISUPAlarmService(config, storage, notifier=notifier)

    # 真的 ISUP 监听也照常起（这样接真盒子也能用）
    threading.Thread(target=service.start, daemon=True).start()

    # 直接在主 app 上加模拟路由 —— 不要在 /api 上 mount，
    # 那样会把所有路径加上 /api 前缀，导致 /api/alarms 变成 /api/api/alarms
    app = create_app(storage, config, alarm_service=service, notifier=notifier)

    @app.post("/simulate")
    def simulate(event_type: str = "vest", pictures: int = 1):
        """灌一条假报警，走和真实回调一样的处理链路。"""
        preset = EVENT_PRESETS.get(event_type)
        if preset is None:
            return {"ok": False, "error": f"未知类型 {event_type}，可选 {list(EVENT_PRESETS)}"}

        pics = [TINY_JPEG] * max(0, pictures)
        fake = FakeAlarm(preset["payload"], pics)
        service._on_alarm_msg(0, fake.pointer(), None)

        # 等 worker 处理完（回调只入队，真正落库在 worker 线程）
        deadline = time.time() + 5
        before = len(storage.list_alarms(limit=500))
        while time.time() < deadline:
            rows = storage.list_alarms(limit=500)
            if len(rows) > before:
                break
            time.sleep(0.05)

        rows = storage.list_alarms(limit=1)
        latest = rows[0] if rows else None
        return {
            "ok": latest is not None,
            "event_type": preset["label"],
            "pictures": len(pics),
            "alarm_id": latest["id"] if latest else None,
            "picture_urls": json.loads(latest["picture_paths"]) if latest else [],
        }

    print()
    print("=" * 66)
    print("  模拟模式已启动（服务和正式启动完全一样，只是多了 /simulate）")
    print(f"  监控页   : http://127.0.0.1:{port}/")
    print(f"  告警列表 : http://127.0.0.1:{port}/api/alarms")
    print(f"  注入接口 : POST http://127.0.0.1:{port}/simulate?event_type=vest&pictures=1")
    print(f"  设备端口 : 7660(注册) / 7661(报警)  ← 接真盒子时用这两个")
    print("=" * 66)
    print()

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def inject_once(base_url, event_type, pictures):
    import urllib.request

    url = f"{base_url}/simulate?event_type={event_type}&pictures={pictures}"
    req = urllib.request.Request(url, method="POST", data=b"")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="模拟 ISUP 报警，验证软件链路")
    parser.add_argument("--start", action="store_true", help="起一个带模拟注入接口的服务")
    parser.add_argument("--port", type=int, default=18080, help="模拟服务端口")
    parser.add_argument("--base", default=None, help="已运行的服务地址，如 http://127.0.0.1:8080")
    parser.add_argument("--count", type=int, default=1, help="灌几条")
    parser.add_argument("--interval", type=float, default=1.5, help="每条间隔秒数")
    parser.add_argument(
        "--type",
        default="vest",
        choices=list(EVENT_PRESETS),
        help="事件类型",
    )
    parser.add_argument("--no-picture", action="store_true", help="不带图片")
    args = parser.parse_args()

    if args.start:
        run_server_with_sim(args.port)
        return 0

    base = args.base or f"http://127.0.0.1:{args.port}"
    pictures = 0 if args.no_picture else 1

    print(f"往 {base} 注入 {args.count} 条 [{args.type}] 报警...")
    for index in range(args.count):
        try:
            result = inject_once(base, args.type, pictures)
            print(f"  [{index + 1}/{args.count}] {result}")
        except Exception as exc:
            print(f"  [{index + 1}/{args.count}] 失败: {type(exc).__name__}: {exc}")
            print(f"  提示: 先起模拟服务 → python tools/simulate_alarm.py --start")
            return 1
        if index < args.count - 1:
            time.sleep(args.interval)

    print()
    print(f"去看结果:")
    print(f"  {base}/              监控页")
    print(f"  {base}/api/alarms    告警列表(JSON)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
