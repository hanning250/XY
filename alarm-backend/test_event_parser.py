# -*- coding: utf-8 -*-
import json
import unittest

from event_parser import is_ppe_related, parse_isapi_payload


SAMPLE_PPE_JSON = {
    "EventNotificationAlert": {
        "dateTime": "2026-09-11T14:00:00+08:00",
        "eventType": "AIOP_Video",
        "eventDescription": "未穿反光衣",
        "channelID": 3,
        "ruleName": "防护服检测规则1",
    }
}

SAMPLE_HELMET_JSON = {
    "dateTime": "2026-09-11T14:01:00+08:00",
    "eventType": "safetyHelmetDetection",
    "eventDescription": "未佩戴安全帽",
    "channelID": 1,
}


class EventParserTest(unittest.TestCase):
    def test_parse_ppe_json(self):
        parsed = parse_isapi_payload(json.dumps(SAMPLE_PPE_JSON).encode("utf-8"))
        self.assertEqual(parsed["channel_no"], 3)
        self.assertIn("反光", parsed["event_type"] + parsed.get("event_description", ""))

    def test_is_ppe_related_by_keyword(self):
        parsed = parse_isapi_payload(json.dumps(SAMPLE_PPE_JSON).encode("utf-8"))
        self.assertTrue(
            is_ppe_related(parsed["event_type"], parsed["raw_text"], ["防护"], parsed=parsed)
        )

    def test_is_ppe_related_helmet(self):
        parsed = parse_isapi_payload(json.dumps(SAMPLE_HELMET_JSON).encode("utf-8"))
        self.assertTrue(
            is_ppe_related(parsed["event_type"], parsed["raw_text"], [], parsed=parsed)
        )


if __name__ == "__main__":
    unittest.main()
