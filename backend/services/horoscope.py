"""
Horoscope service — read-through cache on top of the editorial DB and the
existing astrosage scraper.

Flow for `get_horoscope(sign, period, date, language, tz)`:

  1. Compute `period_key` for (period, date) so this row is uniquely keyed
     to the calendar window it describes (day / ISO-week / month / year).
  2. SELECT from `horoscope_predictions`. If a row exists for that key,
     return it — no network, no parsing.
  3. On miss, only scrape if the requested `period_key` matches the
     CURRENT period_key in `tz`. Archive lookups for past/future periods
     return None so the router can 404 instead of poisoning the cache
     with current text labeled to a wrong key.
  4. Build the astrosage URL, fetch via the shared cached fetcher
     (writes raw HTML into `scraped_pages` and respects the 1 req/s
     throttle), parse with `parsers.horoscope.parse_horoscope`, UPSERT
     into `horoscope_predictions`, return the new row.

All endpoints share a single language at a time. Multi-language fan-out
is the caller's responsibility (one request per language).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date as Date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from .db import connect_ro, connect_rw
from .scraper import fetch_page
from .scraper.parsers.horoscope import (
    ParsedHoroscope,
    ParsedSignDeepDive,
    parse_horoscope,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

Period = Literal[
    "daily", "tomorrow", "weekly", "weekly_love",
    "monthly", "next_month", "yearly",
]

PERIODS: tuple[Period, ...] = (
    "daily", "tomorrow", "weekly", "weekly_love",
    "monthly", "next_month", "yearly",
)

SIGNS: tuple[str, ...] = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)

HOST = "https://www.astrosage.com"

# {period -> path template} for the canonical astrosage slug per period.
# All 12 signs use the same template — only the sign token changes.
URL_TEMPLATES: dict[Period, str] = {
    "daily":       "{host}/horoscope/daily-{sign}-horoscope.asp",
    "tomorrow":    "{host}/horoscope/{sign}-tomorrow-horoscope.asp",
    "weekly":      "{host}/horoscope/weekly-{sign}-horoscope.asp",
    "weekly_love": "{host}/horoscope/weekly-{sign}-love-horoscope.asp",
    "monthly":     "{host}/horoscope/monthly-{sign}-horoscope.asp",
    "next_month":  "{host}/horoscope/next-month-{sign}-horoscope.asp",
    "yearly":      "{host}/horoscope/yearly-{sign}-horoscope.asp",
}


def build_url(sign: str, period: Period) -> str:
    return URL_TEMPLATES[period].format(host=HOST, sign=sign)


# ---------------------------------------------------------------------------
# Period key — buckets a request to the calendar window it describes.
# ---------------------------------------------------------------------------

def _add_months(d: Date, n: int) -> Date:
    # Day-1 anchor avoids month-overflow ambiguity (Jan 31 + 1 → Feb 28/29).
    m = d.month - 1 + n
    return Date(d.year + m // 12, m % 12 + 1, 1)


def period_key(period: Period, d: Date) -> str:
    if period == "daily":
        return d.isoformat()
    if period == "tomorrow":
        return (d + timedelta(days=1)).isoformat()
    if period in ("weekly", "weekly_love"):
        iso_year, iso_week, _ = d.isocalendar()
        return f"{iso_year:04d}-W{iso_week:02d}"
    if period == "monthly":
        return f"{d.year:04d}-{d.month:02d}"
    if period == "next_month":
        nm = _add_months(d, 1)
        return f"{nm.year:04d}-{nm.month:02d}"
    if period == "yearly":
        return f"{d.year:04d}"
    raise ValueError(f"Unknown period: {period!r}")


def current_period_key(period: Period, tz: str) -> str:
    today = datetime.now(ZoneInfo(tz)).date()
    return period_key(period, today)


# ---------------------------------------------------------------------------
# DB layer
# ---------------------------------------------------------------------------

_SELECT_COLS = (
    "sign, period, language, period_key, date_label, prediction, love, "
    "career, finance, health, family, advice, ratings_json, source_url, scraped_at"
)


def _row_to_dict(row) -> dict:
    out = {k: row[k] for k in row.keys()}
    # Deserialize the JSON ratings dict for caller convenience.
    raw = out.pop("ratings_json", None)
    out["ratings"] = json.loads(raw) if raw else None
    return out


def _select(sign: str, period: Period, language: str, key: str) -> dict | None:
    conn = connect_ro()
    try:
        row = conn.execute(
            f"SELECT {_SELECT_COLS} FROM horoscope_predictions "
            "WHERE sign=? AND period=? AND language=? AND period_key=?",
            (sign, period, language, key),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row) if row else None


def _upsert(parsed: ParsedHoroscope, key: str) -> None:
    ratings_json = json.dumps(parsed.ratings, separators=(",", ":")) if parsed.ratings else None
    conn = connect_rw()
    try:
        conn.execute(
            """
            INSERT INTO horoscope_predictions (
                sign, period, language, period_key, date_label,
                prediction, love, career, finance, health, family, advice,
                ratings_json, source_url, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(sign, period, language, period_key) DO UPDATE SET
                date_label   = excluded.date_label,
                prediction   = excluded.prediction,
                love         = excluded.love,
                career       = excluded.career,
                finance      = excluded.finance,
                health       = excluded.health,
                family       = excluded.family,
                advice       = excluded.advice,
                ratings_json = excluded.ratings_json,
                source_url   = excluded.source_url,
                scraped_at   = datetime('now')
            """,
            (
                parsed.sign, parsed.period, parsed.language, key, parsed.date_label,
                parsed.prediction, parsed.love, parsed.career, parsed.finance,
                parsed.health, parsed.family, parsed.advice, ratings_json,
                parsed.source_url,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _upsert_deepdive(d: ParsedSignDeepDive) -> None:
    """Opportunistic UPSERT into `zodiac_signs` from a daily-page parse.
    Only touches the deep-dive columns; existing summary/traits/love/
    compatibility (filled by the sign_intro flow) are preserved via
    COALESCE if this row was created by the daily flow first.
    """
    conn = connect_rw()
    try:
        conn.execute(
            """
            INSERT INTO zodiac_signs (
                id, language, overview, physical_appearance, mental_ability,
                characteristics, aspects_of_life, twelve_houses,
                source_url, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id, language) DO UPDATE SET
                overview            = COALESCE(excluded.overview,            zodiac_signs.overview),
                physical_appearance = COALESCE(excluded.physical_appearance, zodiac_signs.physical_appearance),
                mental_ability      = COALESCE(excluded.mental_ability,      zodiac_signs.mental_ability),
                characteristics     = COALESCE(excluded.characteristics,     zodiac_signs.characteristics),
                aspects_of_life     = COALESCE(excluded.aspects_of_life,     zodiac_signs.aspects_of_life),
                twelve_houses       = COALESCE(excluded.twelve_houses,       zodiac_signs.twelve_houses),
                source_url          = excluded.source_url,
                scraped_at          = datetime('now')
            """,
            (
                d.sign, d.language, d.overview, d.physical_appearance,
                d.mental_ability, d.characteristics, d.aspects_of_life,
                d.twelve_houses, d.source_url,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public service entry point
# ---------------------------------------------------------------------------

async def get_horoscope(
    *,
    sign: str,
    period: Period,
    d: Date,
    language: str = "en",
    tz: str = "Asia/Kolkata",
    force: bool = False,
) -> dict | None:
    """
    Return one horoscope row as a plain dict. Lazy-load from astrosage if
    the (sign, period, language, period_key) combo isn't in DB AND the
    period_key matches the current period in `tz`. Past/future periods
    return None on miss so the caller can 404.

    `force=True` re-scrapes even if cached — useful for admin re-runs after
    parser improvements.
    """
    if sign not in SIGNS:
        raise ValueError(f"Unknown sign: {sign!r}")
    if period not in URL_TEMPLATES:
        raise ValueError(f"Unknown period: {period!r}")

    key = period_key(period, d)

    if not force:
        cached = _select(sign, period, language, key)
        if cached is not None:
            return cached

    if not force and key != current_period_key(period, tz):
        return None  # archive miss — caller should 404

    url = build_url(sign, period)
    html = await fetch_page(
        url, scope="horoscope", ref_id=sign, language=language, force=force,
    )
    parsed = parse_horoscope(html, url, sign=sign, period=period, language=language)
    _upsert(parsed, key)
    # The daily page also carries sign-level evergreen sections; harvest
    # them into zodiac_signs so /v1/reference/zodiac-signs/{id} has them
    # without a second fetch.
    if parsed.sign_deepdive is not None:
        _upsert_deepdive(parsed.sign_deepdive)
    return _select(sign, period, language, key)
