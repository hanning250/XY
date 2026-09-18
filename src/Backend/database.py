# -*- coding: utf-8 -*-
"""SQLite persistence for normalized alarm events."""
import sqlite3
from contextlib import contextmanager
from typing import Any, Optional

from src.Backend.alarm_parser import enrich_alarm_event
from src.Backend.config import DATA_DIR, DB_PATH
from src.Backend.schemas import AlarmEventIn, AlarmEventOut, AlarmStats

SCHEMA = """
CREATE TABLE IF NOT EXISTS alarms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    handle INTEGER,
    alarm_type INTEGER NOT NULL,
    device_id TEXT,
    event_type TEXT,
    event_state TEXT,
    io_port TEXT,
    date_time TEXT,
    channel_name TEXT,
    channel_id TEXT,
    isapi_data_type INTEGER,
    pictures_number INTEGER,
    raw_xml TEXT,
    raw_json TEXT,
    cms_user_id INTEGER,
    rule_name TEXT,
    attr_value INTEGER,
    attr_label TEXT,
    attr_conf INTEGER,
    image_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_alarms_device_id ON alarms(device_id);
CREATE INDEX IF NOT EXISTS idx_alarms_event_type ON alarms(event_type);
CREATE INDEX IF NOT EXISTS idx_alarms_event_state ON alarms(event_state);
CREATE INDEX IF NOT EXISTS idx_alarms_created_at ON alarms(created_at);
"""

MIGRATIONS = (
    "ALTER TABLE alarms ADD COLUMN rule_name TEXT",
    "ALTER TABLE alarms ADD COLUMN attr_value INTEGER",
    "ALTER TABLE alarms ADD COLUMN attr_label TEXT",
    "ALTER TABLE alarms ADD COLUMN attr_conf INTEGER",
    "ALTER TABLE alarms ADD COLUMN image_path TEXT",
)


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        for sql in MIGRATIONS:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_alarm(row: sqlite3.Row) -> AlarmEventOut:
    return AlarmEventOut(
        id=row["id"],
        handle=row["handle"],
        alarm_type=row["alarm_type"],
        device_id=row["device_id"],
        event_type=row["event_type"],
        event_state=row["event_state"],
        io_port=row["io_port"],
        date_time=row["date_time"],
        channel_name=row["channel_name"],
        channel_id=row["channel_id"],
        isapi_data_type=row["isapi_data_type"],
        pictures_number=row["pictures_number"],
        raw_xml=row["raw_xml"],
        raw_json=row["raw_json"],
        cms_user_id=row["cms_user_id"],
        rule_name=row["rule_name"],
        attr_value=row["attr_value"],
        attr_label=row["attr_label"],
        attr_conf=row["attr_conf"],
        image_path=row["image_path"],
        created_at=row["created_at"],
    )


def update_alarm_image_path(image_path: str, alarm_id: Optional[int] = None) -> Optional[int]:
    with get_connection() as conn:
        if alarm_id is None:
            row = conn.execute(
                """
                SELECT id FROM alarms
                WHERE image_path IS NULL OR image_path = ''
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            alarm_id = row["id"]

        conn.execute(
            "UPDATE alarms SET image_path = ? WHERE id = ?",
            (image_path, alarm_id),
        )
        return alarm_id


def delete_alarm(alarm_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
        return cursor.rowcount > 0


def insert_alarm(event: AlarmEventIn) -> AlarmEventOut:
    enriched = enrich_alarm_event(event)
    payload = enriched.model_dump()
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(f":{key}" for key in payload.keys())
    sql = f"INSERT INTO alarms ({columns}) VALUES ({placeholders})"

    with get_connection() as conn:
        cursor = conn.execute(sql, payload)
        row = conn.execute("SELECT * FROM alarms WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _row_to_alarm(row)


def get_alarm(alarm_id: int) -> Optional[AlarmEventOut]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM alarms WHERE id = ?", (alarm_id,)).fetchone()
        return _row_to_alarm(row) if row else None


def list_alarms(
    limit: int = 50,
    offset: int = 0,
    device_id: Optional[str] = None,
    event_type: Optional[str] = None,
    event_state: Optional[str] = None,
) -> tuple[list[AlarmEventOut], int]:
    clauses: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if device_id:
        clauses.append("device_id = :device_id")
        params["device_id"] = device_id
    if event_type:
        clauses.append("event_type = :event_type")
        params["event_type"] = event_type
    if event_state:
        clauses.append("event_state = :event_state")
        params["event_state"] = event_state

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT * FROM alarms
        {where}
        ORDER BY id DESC
        LIMIT :limit OFFSET :offset
    """
    count_sql = f"SELECT COUNT(*) AS total FROM alarms {where}"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total = conn.execute(count_sql, count_params).fetchone()["total"]
        return [_row_to_alarm(row) for row in rows], total


def get_stats() -> AlarmStats:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM alarms").fetchone()["c"]
        active = conn.execute(
            "SELECT COUNT(*) AS c FROM alarms WHERE event_state = 'active'"
        ).fetchone()["c"]
        inactive = conn.execute(
            "SELECT COUNT(*) AS c FROM alarms WHERE event_state = 'inactive'"
        ).fetchone()["c"]

        by_event_type = {
            row["event_type"] or "unknown": row["c"]
            for row in conn.execute(
                "SELECT event_type, COUNT(*) AS c FROM alarms GROUP BY event_type"
            ).fetchall()
        }
        by_device = {
            row["device_id"] or "unknown": row["c"]
            for row in conn.execute(
                "SELECT device_id, COUNT(*) AS c FROM alarms GROUP BY device_id"
            ).fetchall()
        }

    return AlarmStats(
        total=total,
        active=active,
        inactive=inactive,
        by_event_type=by_event_type,
        by_device=by_device,
    )
