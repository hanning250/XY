# -*- coding: utf-8 -*-
"""Track SS-uploaded images and link them to alarm records."""
import re
import threading
import time
from pathlib import Path
from typing import Optional

from src.Backend.config import STORAGE_DIR

_lock = threading.Lock()
_used_images: set[str] = set()
_recent_images: list[tuple[float, str]] = []


def _normalize(path: str) -> str:
    return str(Path(path).resolve())


def register_storage_image(file_path: str) -> None:
    resolved = _normalize(file_path)
    now = time.time()
    with _lock:
        _recent_images.append((now, resolved))
        _recent_images[:] = [
            (ts, path) for ts, path in _recent_images if now - ts <= 300
        ][-50:]


def mark_image_used(file_path: str) -> None:
    with _lock:
        _used_images.add(_normalize(file_path))


def match_storage_by_url(url: str) -> Optional[str]:
    if not url or not STORAGE_DIR.exists():
        return None

    token = url.rsplit("?", 1)[-1].strip()
    if not token:
        return None

    token_upper = token.upper()
    for path in STORAGE_DIR.glob("*"):
        if not path.is_file():
            continue
        if path.stem.upper() == token_upper:
            resolved = _normalize(str(path))
            mark_image_used(resolved)
            return resolved
    return None


def find_unclaimed_recent(within_seconds: int = 120) -> Optional[str]:
    if not STORAGE_DIR.exists():
        return None

    now = time.time()
    candidates: list[tuple[float, str]] = []

    with _lock:
        for path in STORAGE_DIR.glob("*"):
            if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            resolved = _normalize(str(path))
            if resolved in _used_images:
                continue
            mtime = path.stat().st_mtime
            if now - mtime <= within_seconds:
                candidates.append((mtime, resolved))

        for _, path in sorted(_recent_images, reverse=True):
            if path not in _used_images and (now - Path(path).stat().st_mtime) <= within_seconds:
                candidates.append((Path(path).stat().st_mtime, path))

    if not candidates:
        return None

    _, best = max(candidates, key=lambda item: item[0])
    mark_image_used(best)
    return best


def attach_image_to_latest_alarm(image_path: str) -> Optional[int]:
    """Link a late-arriving SS image to the newest alarm without image."""
    from src.Backend.database import update_alarm_image_path

    alarm_id = update_alarm_image_path(image_path)
    if alarm_id is not None:
        mark_image_used(image_path)
    return alarm_id
