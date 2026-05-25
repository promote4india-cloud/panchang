"""
Polite cached HTTP fetcher for astrosage pages (async).

Stores every successful fetch in `scraped_pages` (gzipped HTML). Re-fetch is a
no-op unless `force=True` or the cached row is older than `max_age`. This lets
the scraper be re-run after parser improvements without re-hitting astrosage,
and makes the whole pipeline deterministic.

The HTTP I/O is async (httpx.AsyncClient). The polite 1 req/s throttle is
enforced via an asyncio.Lock so concurrent callers still serialize. SQLite
reads/writes stay synchronous — they're tiny and would add more overhead to
thread-offload than to call inline.

Usage:
    body = await fetch_page(
        "https://panchang.astrosage.com/festival/diwali",
        scope="festival", ref_id="diwali", language="en",
    )

For parsing, call get_cached_page(url) (sync) to read back without touching
the wire.
"""

from __future__ import annotations

import asyncio
import gzip
from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx

from ..db import connect_ro, connect_rw

Scope = Literal[
    "festival", "muhurat", "festival_list", "muhurat_list",
    "horoscope", "horoscope_list",
]

DEFAULT_HEADERS = {
    "User-Agent": "PanchangApp-Scraper/0.1 (+contact: dev@example.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en",
}
DEFAULT_MAX_AGE = timedelta(days=30)
_MIN_DELAY_SEC = 1.0  # polite throttle between live fetches

_throttle_lock = asyncio.Lock()
_last_fetch_ts: float = 0.0


async def _throttle() -> None:
    """Serialize live network fetches and ensure ≥1 s between them."""
    global _last_fetch_ts
    async with _throttle_lock:
        loop = asyncio.get_event_loop()
        gap = loop.time() - _last_fetch_ts
        if gap < _MIN_DELAY_SEC:
            await asyncio.sleep(_MIN_DELAY_SEC - gap)
        _last_fetch_ts = loop.time()


def get_cached_page(url: str) -> str | None:
    """Return cached HTML body for `url` or None."""
    conn = connect_ro()
    try:
        row = conn.execute(
            "SELECT body_gzip FROM scraped_pages WHERE url = ?", (url,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return gzip.decompress(row["body_gzip"]).decode("utf-8", errors="replace")


async def fetch_page(
    url: str,
    *,
    scope: Scope,
    ref_id: str | None,
    language: str = "en",
    force: bool = False,
    max_age: timedelta = DEFAULT_MAX_AGE,
    client: httpx.AsyncClient | None = None,
) -> str:
    """
    Return HTML for `url`, fetching from network only if not cached or stale.
    Always writes/upserts a row in `scraped_pages`.

    Pass `client` to share a single AsyncClient across many calls (saves the
    per-request connection setup); if None, a fresh one-shot client is used.
    """
    if not force:
        cached_row = _peek_cache(url)
        if cached_row is not None:
            fetched_at, body_gzip = cached_row
            if datetime.now(timezone.utc) - fetched_at < max_age:
                return gzip.decompress(body_gzip).decode("utf-8", errors="replace")

    await _throttle()
    headers = {**DEFAULT_HEADERS, "Accept-Language": language}
    if client is None:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=30.0, headers=headers,
        ) as c:
            r = await c.get(url)
    else:
        r = await client.get(url, headers=headers)

    body = r.text
    body_gzip = gzip.compress(body.encode("utf-8"))
    etag = r.headers.get("etag")

    conn = connect_rw()
    try:
        conn.execute(
            """
            INSERT INTO scraped_pages (
                url, scope, ref_id, language, http_status, etag, fetched_at, body_gzip
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
            ON CONFLICT(url) DO UPDATE SET
                scope=excluded.scope,
                ref_id=excluded.ref_id,
                language=excluded.language,
                http_status=excluded.http_status,
                etag=excluded.etag,
                fetched_at=excluded.fetched_at,
                body_gzip=excluded.body_gzip
            """,
            (url, scope, ref_id, language, r.status_code, etag, body_gzip),
        )
        conn.commit()
    finally:
        conn.close()

    r.raise_for_status()
    return body


def _peek_cache(url: str) -> tuple[datetime, bytes] | None:
    conn = connect_ro()
    try:
        row = conn.execute(
            "SELECT fetched_at, body_gzip FROM scraped_pages WHERE url = ?", (url,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    fetched_at = datetime.fromisoformat(row["fetched_at"]).replace(tzinfo=timezone.utc)
    return fetched_at, row["body_gzip"]
