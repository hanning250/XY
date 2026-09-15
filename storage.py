# -*- coding: utf-8 -*-
import json
import os
import sqlite3
import threading
from datetime import datetime


class AlarmStorage:
    def __init__(self, db_path, picture_dir):
        self.db_path = db_path
        self.picture_dir = picture_dir
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        os.makedirs(picture_dir, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alarms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        device_ip TEXT,
                        device_serial TEXT,
                        command_type TEXT,
                        event_type TEXT,
                        channel_no INTEGER,
                        event_time TEXT,
                        raw_payload TEXT,
                        picture_paths TEXT,
                        is_ppe_related INTEGER DEFAULT 0
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def save_alarm(
        self,
        device_ip,
        device_serial,
        command_type,
        event_type,
        channel_no,
        event_time,
        raw_payload,
        picture_paths,
        is_ppe_related,
    ):
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    INSERT INTO alarms (
                        created_at, device_ip, device_serial, command_type,
                        event_type, channel_no, event_time, raw_payload,
                        picture_paths, is_ppe_related
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now().isoformat(timespec="seconds"),
                        device_ip,
                        device_serial,
                        command_type,
                        event_type,
                        channel_no,
                        event_time,
                        raw_payload,
                        json.dumps(picture_paths, ensure_ascii=False),
                        1 if is_ppe_related else 0,
                    ),
                )
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def list_alarms(self, limit=50, ppe_only=False):
        with self._lock:
            conn = self._connect()
            try:
                if ppe_only:
                    rows = conn.execute(
                        """
                        SELECT * FROM alarms
                        WHERE is_ppe_related = 1
                        ORDER BY id DESC LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM alarms ORDER BY id DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def get_alarm(self, alarm_id):
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM alarms WHERE id = ?",
                    (alarm_id,),
                ).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

    def count_alarms(self):
        with self._lock:
            conn = self._connect()
            try:
                total = conn.execute("SELECT COUNT(*) FROM alarms").fetchone()[0]
                ppe = conn.execute(
                    "SELECT COUNT(*) FROM alarms WHERE is_ppe_related = 1"
                ).fetchone()[0]
                return {"total": total, "ppe_related": ppe}
            finally:
                conn.close()
