"""
Shared SQLite helpers for the editorial / scraped content tables.

The database file (data/sqlite.db) is also used by services/locations.py for
GeoNames data. The two layers are kept additive — schema.sql uses CREATE TABLE
IF NOT EXISTS so the GeoNames build never collides with festival tables.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .locations import DB_PATH  # single source of truth for the file path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect_rw() -> sqlite3.Connection:
    """Read-write connection with FK + WAL enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def connect_ro() -> sqlite3.Connection:
    """Read-only connection (preferred for query endpoints)."""
    if not DB_PATH.exists():
        raise RuntimeError(f"Database missing at {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_content_schema() -> None:
    """Apply the additive editorial schema. Safe to call on every startup."""
    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = connect_rw()
    try:
        conn.executescript(ddl)
        conn.commit()
    finally:
        conn.close()
