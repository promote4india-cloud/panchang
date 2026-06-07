"""
Shared PostgreSQL helpers for the editorial / scraped content tables.

Connection is obtained via DATABASE_URL (set in .env locally or injected by
Render in production). Uses psycopg3 (psycopg[binary]) with dict_row so
callers can access columns by name: row["col"] — same interface as before.

Public API
----------
Sync (for background threads — scraper, LLM runners, seed):
    connect_rw()          -> psycopg.Connection  (read-write)
    connect_ro()          -> psycopg.Connection  (read, uses same URL for now)
    ensure_content_schema()                      (apply DDL on startup)

Async (for FastAPI route handlers and async services):
    get_pool()            -> AsyncConnectionPool  (singleton)
    init_pool()           -> None                (call once in lifespan startup)
    close_pool()          -> None                (call in lifespan shutdown)
    async_db()            -> AsyncContextManager[AsyncConnection]
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# ---------------------------------------------------------------------------
# Sync helpers (kept for background threads: scraper, LLM runners, seed)
# ---------------------------------------------------------------------------

def _get_dsn() -> str:
    from backend.config import DATABASE_URL  # local import avoids circular at module load
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Add it to your .env file or set it as an environment variable."
        )
    return DATABASE_URL


def connect_rw() -> psycopg.Connection:
    """Read-write connection with dict_row factory. For sync/thread contexts."""
    return psycopg.connect(_get_dsn(), row_factory=dict_row)


def connect_ro() -> psycopg.Connection:
    """Read connection (uses same URL; Postgres handles concurrency natively). For sync/thread contexts."""
    return psycopg.connect(_get_dsn(), row_factory=dict_row)


# ---------------------------------------------------------------------------
# Async connection pool (for FastAPI route handlers)
# ---------------------------------------------------------------------------

_pool: AsyncConnectionPool | None = None


async def init_pool() -> None:
    """
    Create the async connection pool. Call once inside the FastAPI lifespan
    startup. Uses min_size=0 so Neon free-tier compute can auto-suspend when
    idle; max_size=5 stays under Neon's free-tier connection limit of 10.
    """
    global _pool
    dsn = _get_dsn()
    _pool = AsyncConnectionPool(
        conninfo=dsn,
        min_size=0,
        max_size=5,
        kwargs={"row_factory": dict_row},
        open=False,          # we open manually below so we can await it
        reconnect_timeout=30,
        reconnect_failed=_on_reconnect_failed,
    )
    await _pool.open(wait=True, timeout=30)
    log.info("[db] Async connection pool opened (min_size=0, max_size=5)")


async def close_pool() -> None:
    """Close the pool gracefully. Call in lifespan shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        log.info("[db] Async connection pool closed")


def get_pool() -> AsyncConnectionPool:
    """Return the live pool. Raises if init_pool() has not been called."""
    if _pool is None:
        raise RuntimeError(
            "Async DB pool is not initialised. "
            "Ensure init_pool() was awaited in the FastAPI lifespan startup."
        )
    return _pool


@asynccontextmanager
async def async_db() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """
    Async context manager that borrows a connection from the pool.

    Usage:
        async with async_db() as conn:
            row = await conn.execute("SELECT ...", (...)).fetchone()
    """
    async with get_pool().connection() as conn:
        yield conn


def _on_reconnect_failed(pool: AsyncConnectionPool) -> None:
    log.error(
        "[db] Pool failed to reconnect after %s seconds — Neon compute may be waking up",
        pool.reconnect_timeout,
    )


# ---------------------------------------------------------------------------
# Schema bootstrap (sync — called once at startup via asyncio.to_thread)
# ---------------------------------------------------------------------------

def ensure_content_schema() -> None:
    """Apply the additive editorial schema. Safe to call on every startup."""
    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = connect_rw()
    try:
        # Split on ';' and execute each non-empty statement individually
        # (psycopg3 does not have executescript like sqlite3).
        statements = [s.strip() for s in ddl.split(";") if s.strip()]
        with conn.transaction():
            for stmt in statements:
                conn.execute(stmt)
        _apply_migrations(conn)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Idempotent column migrations
# ---------------------------------------------------------------------------

_MIGRATIONS: list[tuple[str, str, str]] = [
    # (table, column, ALTER statement)
    ("festivals", "scope_traditions",
     "ALTER TABLE festivals ADD COLUMN scope_traditions TEXT"),
    ("horoscope_predictions", "ratings_json",
     "ALTER TABLE horoscope_predictions ADD COLUMN ratings_json TEXT"),
    ("zodiac_signs", "overview",
     "ALTER TABLE zodiac_signs ADD COLUMN overview TEXT"),
    ("zodiac_signs", "physical_appearance",
     "ALTER TABLE zodiac_signs ADD COLUMN physical_appearance TEXT"),
    ("zodiac_signs", "mental_ability",
     "ALTER TABLE zodiac_signs ADD COLUMN mental_ability TEXT"),
    ("zodiac_signs", "characteristics",
     "ALTER TABLE zodiac_signs ADD COLUMN characteristics TEXT"),
    ("zodiac_signs", "aspects_of_life",
     "ALTER TABLE zodiac_signs ADD COLUMN aspects_of_life TEXT"),
    ("zodiac_signs", "twelve_houses",
     "ALTER TABLE zodiac_signs ADD COLUMN twelve_houses TEXT"),
    # LLM cleaning layer
    ("festival_content", "llm_cleaned_at",
     "ALTER TABLE festival_content ADD COLUMN llm_cleaned_at TEXT"),
    ("muhurat_content", "llm_cleaned_at",
     "ALTER TABLE muhurat_content ADD COLUMN llm_cleaned_at TEXT"),
    ("horoscope_predictions", "llm_cleaned_at",
     "ALTER TABLE horoscope_predictions ADD COLUMN llm_cleaned_at TEXT"),
    ("zodiac_signs", "llm_cleaned_at",
     "ALTER TABLE zodiac_signs ADD COLUMN llm_cleaned_at TEXT"),
    # Seed version hash guard
    ("db_meta", "value",
     "ALTER TABLE db_meta ADD COLUMN value TEXT"),
]


def _apply_migrations(conn: psycopg.Connection) -> None:
    # Ensure db_meta table exists first (needed for the seed hash guard)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS db_meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    for table, column, ddl_stmt in _MIGRATIONS:
        row = conn.execute(
            """
            SELECT 1 FROM information_schema.columns
             WHERE table_name = %s AND column_name = %s
            """,
            (table, column),
        ).fetchone()
        if row is None:
            try:
                conn.execute(ddl_stmt)
            except Exception as exc:  # noqa: BLE001
                log.debug("Migration skipped (%s.%s): %s", table, column, exc)
