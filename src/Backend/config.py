# -*- coding: utf-8 -*-
"""Backend configuration."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "src" / "Frontend"
DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = PROJECT_ROOT / "storage"
DB_PATH = DATA_DIR / "alarms.db"

HOST = "0.0.0.0"
PORT = 8080
