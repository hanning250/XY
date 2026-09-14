# -*- coding: utf-8 -*-
"""离线验证 ISUP 报警接收全流程（不需要设备和网络）。

做法：按 SDK 的内存布局手工构造
    NET_EHOME_ALARM_MSG
      ├─ pAlarmInfo -> NET_EHOME_ALARM_ISAPI_INFO
      │                 ├─ pAlarmData  -> AIOP/ISAPI JSON
      │                 └─ pPicPackData-> NET_EHOME_ALARM_ISAPI_PICDATA[n]
      │                                    └─ pPicData -> JPEG 字节
然后直接调 ISUPAlarmService._on_alarm_msg（走真实回调代码路径），
再等 worker 线程消费完，检查图片/JSON/入库结果。

运行： python -m unittest test_isup_alarm -v
"""

import json
import os
import shutil
import sys
import time
import unittest
from ctypes import (
    POINTER,
    addressof,
    byref,
    c_byte,
    c_char_p,
    c_void_p,
    cast,
    create_string_buffer,
    memmove,
    sizeof,
)

# 项目根目录（tests/ 的上一层），保证能 import core/web/common
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.hcisup import (  # noqa: E402
    EHOME_ISAPI_ALARM,
    ENUM_DEV_ON,
    NET_EHOME_ALARM_ISAPI_INFO,
    NET_EHOME_ALARM_ISAPI_PICDATA,
    NET_EHOME_ALARM_MSG,
    NET_EHOME_ALARM_LISTEN_PARAM,
    NET_EHOME_CMS_LISTEN_PARAM,
    NET_EHOME_DEV_REG_INFO_V12,
    REGISTER_TYPE_LABELS,
)
from core.alarm_service import ISUPAlarmService  # noqa: E402
from common.storage import AlarmStorage  # noqa: E402

# 最小合法 JPEG（SOI + APP0 + EOI）
JPEG_1 = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xd9"
)
JPEG_2 = b"\xff\xd8\xff\xe1\x00\x08HIKPIC\x00\xff\xd9"

# 设备下发的 AIOP 算法结果（与 AI 开放平台示例一致）
AIOP_JSON = {
    "width": "704",
    "height": "576",
    "targets": [
        {
            "obj": {
                "modelID": "9f3c-uuid",
                "id": 1,
                "type": 0,
                "confidence": 940,
                "valid": 1,
                "visible": 1,
                "rect": {
                    "x": "0.217483",
                    "y": "0.588785",
                    "w": "0.149191",
                    "h": "0.409346",
                },
            }
        }
    ],
    "events": {"alertInfo": [{"ruleInfo": {"ruleID": 3}}]},
}


def set_field(struct_obj, field_name, data):
    """给 ctypes 结构体里的定长 char/byte 数组字段赋值。

    坑：c_char * N 字段通过实例访问返回的是 **bytes 副本**，
    对它 cast/memmove 只会写进临时对象，结构体里其实没变。
    可靠做法：用「结构体首地址 + 字段偏移」算出真实地址再写。
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    field = getattr(type(struct_obj), field_name)
    addr = addressof(struct_obj) + field.offset
    size = field.size
    memmove(addr, data[:size], min(len(data), size))


class AlarmHarness:
    """按 SDK 内存布局搭一块 [MSG][ISAPI_INFO][JSON][PICDATA[]][JPEG...] 缓冲。"""

    def __init__(self, alarm_json=None, pictures=(JPEG_1,), serial=b"ABC123456789"):
        self.alarm_json = (
            json.dumps(alarm_json, ensure_ascii=False).encode("utf-8")
            if alarm_json is not None
            else b""
        )
        self.pictures = list(pictures)

        isapi_size = sizeof(NET_EHOME_ALARM_ISAPI_INFO)
        pic_struct_size = sizeof(NET_EHOME_ALARM_ISAPI_PICDATA)
        pic_count = len(self.pictures)

        total = (
            sizeof(NET_EHOME_ALARM_MSG)
            + isapi_size
            + len(self.alarm_json)
            + pic_struct_size * max(pic_count, 1)
            + sum(len(p) for p in self.pictures)
        )
        self.buf = create_string_buffer(total)
        base = addressof(self.buf)

        # --- NET_EHOME_ALARM_MSG ---
        self.msg = cast(self.buf, POINTER(NET_EHOME_ALARM_MSG)).contents
        self.msg.dwAlarmType = EHOME_ISAPI_ALARM
        set_field(self.msg, "sSerialNumber", serial)
        self.msg.pAlarmInfo = base + sizeof(NET_EHOME_ALARM_MSG)
        self.msg.dwAlarmInfoLen = isapi_size
        self.msg.pXmlBuf = None
        self.msg.dwXmlBufLen = 0
        self.msg.pHttpUrl = None
        self.msg.dwHttpUrlLen = 0
        self._msg_addr = base

        # --- NET_EHOME_ALARM_ISAPI_INFO ---
        isapi_addr = base + sizeof(NET_EHOME_ALARM_MSG)
        isapi = cast(c_void_p(isapi_addr), POINTER(NET_EHOME_ALARM_ISAPI_INFO)).contents
        isapi.byDataType = 2 if self.alarm_json else 0
        isapi.byPicturesNumber = pic_count

        cursor = isapi_addr + isapi_size
        if self.alarm_json:
            memmove(cursor, self.alarm_json, len(self.alarm_json))
            isapi.pAlarmData = cast(c_void_p(cursor), c_char_p)
            isapi.dwAlarmDataLen = len(self.alarm_json)
            cursor += len(self.alarm_json)
        else:
            isapi.pAlarmData = None
            isapi.dwAlarmDataLen = 0

        if pic_count:
            isapi.pPicPackData = cursor
            pic_array_addr = cursor
            data_cursor = cursor + pic_struct_size * pic_count
            for index, data in enumerate(self.pictures):
                item_addr = pic_array_addr + pic_struct_size * index
                item = cast(
                    c_void_p(item_addr), POINTER(NET_EHOME_ALARM_ISAPI_PICDATA)
                ).contents
                item.dwPicLen = len(data)
                set_field(item, "szFilename", f"pic_{index}.jpg")
                item.pPicData = cast(c_void_p(data_cursor), POINTER(c_byte))
                memmove(data_cursor, data, len(data))
                data_cursor += len(data)
        else:
            isapi.pPicPackData = None

    def msg_pointer(self):
        return cast(c_void_p(self._msg_addr), POINTER(NET_EHOME_ALARM_MSG))


class TestIsupAlarm(unittest.TestCase):
    def setUp(self):
        # 固定路径（不用 mkdtemp，避免沙箱对新建目录的限制）
        self.tmp = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_test_tmp", "isup_case"
        )
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.storage = AlarmStorage(
            db_path=os.path.join(self.tmp, "alarms.db"),
            picture_dir=os.path.join(self.tmp, "pictures"),
        )
        self.config = {
            "event_filter_keywords": ["反光衣", "安全帽", "防护"],
            "aiop_type_labels": {"0": "未穿反光衣", "1": "未戴安全帽"},
            "isup": {},
        }
        self.service = ISUPAlarmService(self.config, self.storage)

    def tearDown(self):
        self.service.running = False
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _drain(self, expect_rows=1, timeout=5):
        """等 worker 真正处理完：以「库里出现预期条数」为准，避免竞态。"""
        return self._wait_for(
            lambda: len(self.storage.list_alarms(limit=50)) >= expect_rows,
            timeout=timeout,
        )

    @staticmethod
    def _wait_for(predicate, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return False

    # ---------------- 结构体布局 ----------------

    def test_struct_layout(self):
        """布局不对会把图片读成乱码，先卡住。"""
        self.assertEqual(sizeof(NET_EHOME_ALARM_MSG), 72)
        self.assertEqual(sizeof(NET_EHOME_ALARM_ISAPI_INFO), 56)
        self.assertEqual(sizeof(NET_EHOME_ALARM_ISAPI_PICDATA), 272)
        self.assertEqual(NET_EHOME_ALARM_MSG.dwAlarmType.offset, 0)
        self.assertEqual(NET_EHOME_ALARM_MSG.pAlarmInfo.offset, 8)
        self.assertEqual(NET_EHOME_ALARM_MSG.pHttpUrl.offset, 48)
        self.assertEqual(NET_EHOME_ALARM_ISAPI_INFO.pAlarmData.offset, 0)
        self.assertEqual(NET_EHOME_ALARM_ISAPI_INFO.pPicPackData.offset, 16)
        self.assertEqual(NET_EHOME_ALARM_ISAPI_PICDATA.dwPicLen.offset, 0)
        self.assertEqual(NET_EHOME_ALARM_ISAPI_PICDATA.pPicData.offset, 264)

    # ---------------- 设备注册 ----------------

    def test_device_online_tracked(self):
        """设备上线要能被记录，并带上设备ID/序列号。"""
        dev = NET_EHOME_DEV_REG_INFO_V12()
        set_field(dev.struRegInfo, "byDeviceID", b"DEV-TEST-001")
        set_field(dev.struRegInfo, "sDeviceSerial", b"SN0000000001")
        set_field(dev.struRegInfo, "byDevProtocolVersion", b"4.0")
        set_field(dev, "sDevName", "测试盒子")
        set_field(dev.struRegInfo.struDevAdd, "szIP", b"192.168.1.64")
        dev.struRegInfo.struDevAdd.wPort = 7660

        self.service._on_device_register(
            login_id=7,
            data_type=ENUM_DEV_ON,
            p_out_buffer=addressof(dev),
            out_len=sizeof(dev),
            p_in_buffer=None,
            in_len=0,
            user=None,
        )
        # 设备注册不产生告警，等状态更新而不是等告警条数
        self.assertTrue(self._wait_for(lambda: self.service.status["devices_online"] == 1))

        status = self.service.status
        self.assertEqual(status["devices_online"], 1)
        device = status["devices"][0]
        self.assertEqual(device["device_id"], "DEV-TEST-001")
        self.assertEqual(device["serial"], "SN0000000001")
        self.assertEqual(device["device_ip"], "192.168.1.64")
        self.assertEqual(device["protocol_version"], "4.0")
        self.assertEqual(device["state"], "online")

    # ---------------- 报警 + 图片 ----------------

    def test_alarm_with_pictures_end_to_end(self):
        """核心用例：报警回调 → 入队 → worker 存图/解析/入库。"""
        harness = AlarmHarness(alarm_json=AIOP_JSON, pictures=(JPEG_1, JPEG_2))

        # 走真实回调入口（内部只拷贝+入队）
        self.service._on_alarm_msg(0, harness.msg_pointer(), None)
        self.assertTrue(self._drain(), "worker 未在超时内消费完队列")

        rows = self.storage.list_alarms(limit=10)
        self.assertEqual(len(rows), 1, "应当入库一条告警")
        row = rows[0]

        # 图片：两张都落盘，且字节完全一致
        paths = json.loads(row["picture_paths"])
        self.assertEqual(len(paths), 2, "应当保存 2 张图片")
        for path, expected in zip(paths, (JPEG_1, JPEG_2)):
            self.assertTrue(os.path.isfile(path), f"图片不存在: {path}")
            with open(path, "rb") as fp:
                self.assertEqual(fp.read(), expected)
        self.assertTrue(paths[0].endswith(".jpg"))

        # AIOP 算法结果解析
        analysis = json.loads(row["analysis"])
        self.assertTrue(analysis["parsed"])
        self.assertEqual(analysis["confidence"], 940)
        self.assertEqual(analysis["target_count"], 1)
        self.assertEqual(analysis["label"], "未穿反光衣")
        self.assertAlmostEqual(analysis["rect"]["w"], 0.149191)

        # event_type 用上了中文标签，PPE 判定命中
        self.assertEqual(row["event_type"], "未穿反光衣")
        self.assertEqual(row["is_ppe_related"], 1)

        # 详情里有设备与图片信息
        detail = json.loads(row["event_detail"])
        self.assertEqual(detail["alarm_type"], EHOME_ISAPI_ALARM)
        self.assertEqual(detail["pictures_number"], 2)
        self.assertTrue(os.path.isfile(detail["aiop_json_path"]))
        self.assertEqual(detail["picture_notes"], [])

    def test_alarm_without_picture(self):
        """设备只给 JSON 不给图，也不能丢告警。"""
        harness = AlarmHarness(alarm_json=AIOP_JSON, pictures=())
        self.service._on_alarm_msg(0, harness.msg_pointer(), None)
        self.assertTrue(self._drain())

        rows = self.storage.list_alarms(limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0]["picture_paths"]), [])
        self.assertEqual(json.loads(rows[0]["analysis"])["confidence"], 940)

    def test_non_isapi_alarm_still_recorded(self):
        """非 ISAPI 类型的报警（如门禁/热度图）也要落库，便于后续补解析。"""
        self.service._on_alarm_msg(
            0,
            self._raw_msg(alarm_type=5, text=b"<EventNotificationAlert/>"),
            None,
        )
        self.assertTrue(self._drain())

        rows = self.storage.list_alarms(limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "isup_ehome_alarm_cid_report")
        # 原始 XML 与报警类型都应保留下来，便于后续补解析
        self.assertIn("<EventNotificationAlert/>", rows[0]["raw_payload"])
        detail = json.loads(rows[0]["event_detail"])
        self.assertEqual(detail["alarm_type_label"], "EHOME_ALARM_CID_REPORT")

    def test_plain_isapi_json_not_aiop(self):
        """普通 ISAPI 事件（没有 targets）走 eventType 分支，不能误判成 AIOP。"""
        payload = {
            "EventNotificationAlert": {
                "dateTime": "2026-09-11T14:00:00+08:00",
                "eventType": "safetyHelmetDetection",
                "eventDescription": "未佩戴安全帽",
                "channelID": 3,
            }
        }
        harness = AlarmHarness(alarm_json=payload, pictures=(JPEG_1,))
        self.service._on_alarm_msg(0, harness.msg_pointer(), None)
        self.assertTrue(self._drain())

        rows = self.storage.list_alarms(limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["channel_no"], 3)
        self.assertEqual(rows[0]["event_type"], "safetyHelmetDetection")
        self.assertEqual(rows[0]["is_ppe_related"], 1, "关键词“安全帽”应判定为 PPE")
        analysis = json.loads(rows[0]["analysis"])
        self.assertNotIn("targets", analysis)

    def test_callback_is_fast_and_defers_work(self):
        """回调必须只入队：耗时要远低于 SDK 要求的 10ms，重活交给 worker。

        注意：不能断言「回调返回时图片一定还没落盘」——worker 线程是并发的，
        它可能在断言前就写完了，那属于正常情况。这里改为断言回调本身的延迟。
        """
        harness = AlarmHarness(alarm_json=AIOP_JSON, pictures=(JPEG_1,))

        start = time.perf_counter()
        self.service._on_alarm_msg(0, harness.msg_pointer(), None)
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.assertEqual(self.service.status["received_alarms"], 1)
        self.assertLess(
            elapsed_ms,
            10.0,
            f"报警回调耗时 {elapsed_ms:.2f}ms，超过 SDK 要求的 10ms（说明回调里干了重活）",
        )

        # worker 负责真正的落盘
        self.assertTrue(self._drain())
        paths = json.loads(self.storage.list_alarms(limit=5)[0]["picture_paths"])
        self.assertEqual(len(paths), 1)
        with open(paths[0], "rb") as fp:
            self.assertEqual(fp.read(), JPEG_1)

    # 工具：只有 text 的简单 MSG
    def _raw_msg(self, alarm_type, text=b""):
        # 缓冲区挂到 self 上，避免函数返回后 ctypes 对象被回收导致悬空指针
        self._raw_buf = create_string_buffer(4096)
        msg = cast(self._raw_buf, POINTER(NET_EHOME_ALARM_MSG)).contents
        msg.dwAlarmType = alarm_type
        set_field(msg, "sSerialNumber", b"ABC123456789")
        if text:
            addr = addressof(self._raw_buf) + sizeof(NET_EHOME_ALARM_MSG)
            memmove(addr, text, len(text))
            msg.pXmlBuf = addr
            msg.dwXmlBufLen = len(text)
        return cast(self._raw_buf, POINTER(NET_EHOME_ALARM_MSG))


if __name__ == "__main__":
    unittest.main(verbosity=2)
