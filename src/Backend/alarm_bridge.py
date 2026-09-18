# -*- coding: utf-8 -*-
"""Thread-safe bridge from SDK alarm callback to FastAPI."""
import queue

from src.Backend.schemas import AlarmEventIn

_alarm_queue: queue.Queue[AlarmEventIn] = queue.Queue()


def enqueue_alarm(event: AlarmEventIn) -> None:
    _alarm_queue.put(event)


def get_alarm_queue() -> queue.Queue[AlarmEventIn]:
    return _alarm_queue


def register_sdk_handler() -> None:
    from src.Common import glo

    def handler(event_dict: dict) -> None:
        enqueue_alarm(AlarmEventIn(**event_dict))

    glo.set_value("alarm_event_handler", handler)


def unregister_sdk_handler() -> None:
    from src.Common import glo

    glo.set_value("alarm_event_handler", None)
