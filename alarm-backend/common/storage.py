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
                self._migrate(conn)
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _migrate(conn):
        """给旧库补上新增字段，避免升级后需要手工删库。"""
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(alarms)").fetchall()
        }
        additions = {
            "analysis": "TEXT",  # AIOP 解析后的结构化结果（JSON）
            "event_detail": "TEXT",  # 事件附加信息：taskID/MPID/置信度等（JSON）
        }
        for column, column_type in additions.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE alarms ADD COLUMN {column} {column_type}")
                print(f"[storage] 已为 alarms 表新增字段: {column}")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alarms_is_ppe ON alarms (is_ppe_related, id DESC)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alarms_event_time ON alarms (event_time)")

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
        analysis=None,
        event_detail=None,
    ):
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    INSERT INTO alarms (
                        created_at, device_ip, device_serial, command_type,
                        event_type, channel_no, event_time, raw_payload,
                        picture_paths, is_ppe_related, analysis, event_detail
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        analysis,
                        event_detail,
                    ),
                )
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def list_alarms(
        self,
        limit=50,
        offset=0,
        ppe_only=False,
        start_time=None,
        end_time=None,
        channel_no=None,
    ):
        clauses = []
        params = []
        if ppe_only:
            clauses.append("is_ppe_related = 1")
        if start_time:
            clauses.append("COALESCE(event_time, created_at) >= ?")
            params.append(start_time)
        if end_time:
            clauses.append("COALESCE(event_time, created_at) <= ?")
            params.append(end_time)
        if channel_no is not None:
            clauses.append("channel_no = ?")
            params.append(channel_no)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])

        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    f"""
                    SELECT * FROM alarms
                    {where}
                    ORDER BY id DESC LIMIT ? OFFSET ?
                    """,
                    params,
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
