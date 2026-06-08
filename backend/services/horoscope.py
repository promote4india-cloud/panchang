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

import asyncio
import json
import logging
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

log = logging.getLogger("services.horoscope")

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
    "career, finance, health, family, advice, ratings_json, source_url, "
    "scraped_at, llm_cleaned_at"
)


def _row_to_dict(row) -> dict:
    out = dict(row)
    # Deserialize the JSON ratings dict for caller convenience.
    raw = out.pop("ratings_json", None)
    out["ratings"] = json.loads(raw) if raw else None
    return out


def _select(sign: str, period: Period, language: str, key: str) -> dict | None:
    conn = connect_ro()
    try:
        row = conn.execute(
            f"SELECT {_SELECT_COLS} FROM horoscope_predictions "
            "WHERE sign=%s AND period=%s AND language=%s AND period_key=%s",
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
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
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
                scraped_at   = NOW()
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
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT(id, language) DO UPDATE SET
                overview            = COALESCE(excluded.overview,            zodiac_signs.overview),
                physical_appearance = COALESCE(excluded.physical_appearance, zodiac_signs.physical_appearance),
                mental_ability      = COALESCE(excluded.mental_ability,      zodiac_signs.mental_ability),
                characteristics     = COALESCE(excluded.characteristics,     zodiac_signs.characteristics),
                aspects_of_life     = COALESCE(excluded.aspects_of_life,     zodiac_signs.aspects_of_life),
                twelve_houses       = COALESCE(excluded.twelve_houses,       zodiac_signs.twelve_houses),
                source_url          = excluded.source_url,
                scraped_at          = NOW()
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
# On-demand clean + translate (single combined LLM call)
# ---------------------------------------------------------------------------

# Guards against firing duplicate clean+translate jobs for the same row while
# one is already in flight, and keeps a strong reference to the background
# tasks so they aren't garbage-collected mid-run. Both reset on process
# restart, which is fine — the work is idempotent and re-triggers on the next
# cache miss.
_inflight_clean: set[tuple[str, str, str]] = set()
_bg_tasks: set[asyncio.Task] = set()


def _apply_clean_translate(en_row: dict, lang_map: dict[str, dict], key: str) -> None:
    """
    Write the result of a combined clean+translate call back to the DB:
      - "en"  → UPDATE the existing raw row with cleaned text + llm_cleaned_at
      - others → UPSERT a per-language row
    """
    sign, period = en_row["sign"], en_row["period"]
    conn = connect_rw()
    try:
        for lang, fields in lang_map.items():
            if not isinstance(fields, dict) or not fields:
                continue

            if lang == "en":
                # COALESCE so a field the LLM omitted never nulls existing text.
                conn.execute(
                    """
                    UPDATE horoscope_predictions SET
                        prediction = COALESCE(%s, prediction),
                        love       = COALESCE(%s, love),
                        career     = COALESCE(%s, career),
                        finance    = COALESCE(%s, finance),
                        health     = COALESCE(%s, health),
                        family     = COALESCE(%s, family),
                        advice     = COALESCE(%s, advice),
                        llm_cleaned_at = NOW()
                    WHERE sign=%s AND period=%s AND language='en' AND period_key=%s
                    """,
                    (
                        fields.get("prediction"), fields.get("love"), fields.get("career"),
                        fields.get("finance"), fields.get("health"), fields.get("family"),
                        fields.get("advice"),
                        sign, period, key,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO horoscope_predictions
                        (sign, period, language, period_key, date_label,
                         prediction, love, career, finance, health, family, advice,
                         source_url, llm_cleaned_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                    ON CONFLICT (sign, period, language, period_key) DO UPDATE SET
                        date_label  = COALESCE(excluded.date_label, horoscope_predictions.date_label),
                        prediction  = excluded.prediction,
                        love        = excluded.love,
                        career      = excluded.career,
                        finance     = excluded.finance,
                        health      = excluded.health,
                        family      = excluded.family,
                        advice      = excluded.advice,
                        llm_cleaned_at = NOW()
                    """,
                    (
                        sign, period, lang, key, en_row.get("date_label"),
                        fields.get("prediction"), fields.get("love"), fields.get("career"),
                        fields.get("finance"), fields.get("health"), fields.get("family"),
                        fields.get("advice"),
                        en_row.get("source_url"),
                    ),
                )
        conn.commit()
    finally:
        conn.close()


async def _run_clean_translate(sign: str, period: Period, key: str, en_row: dict) -> None:
    """Background worker: one combined clean+translate LLM call for a single
    English row, then write all languages back. Never raises."""
    try:
        from .content_cleaner import clean_and_translate_horoscope_batch

        result = await clean_and_translate_horoscope_batch([en_row])
        if not result:
            return  # LLM disabled or call failed — raw row stays; retried next miss
        lang_map = result.get(f"{sign}|{period}|en|{key}")
        if not lang_map:
            log.warning("clean+translate: no entry for %s/%s/%s", sign, period, key)
            return
        _apply_clean_translate(en_row, lang_map, key)
        log.info(
            "clean+translate done for %s/%s/%s (%d languages)",
            sign, period, key, len(lang_map),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("clean+translate failed for %s/%s/%s: %s", sign, period, key, exc)


def _schedule_clean_translate(sign: str, period: Period, key: str, en_row: dict) -> None:
    """
    Fire-and-forget a combined clean+translate for one row. Cheap and safe:
      - de-dupes via ``_inflight_clean`` so concurrent requests for the same
        row don't stack jobs
      - returns silently if called outside a running event loop
    The user's request returns immediately; the cache self-upgrades to cleaned
    English + 11 translations shortly after.
    """
    sig = (sign, period, key)
    if sig in _inflight_clean:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # not in an async context — nothing to schedule onto

    _inflight_clean.add(sig)
    task = loop.create_task(_run_clean_translate(sign, period, key, en_row))
    _bg_tasks.add(task)
    task.add_done_callback(
        lambda t: (_bg_tasks.discard(t), _inflight_clean.discard(sig))
    )


# ---------------------------------------------------------------------------
# Public service entry point
# ---------------------------------------------------------------------------

async def _scrape_en(sign: str, period: Period, key: str, *, force: bool) -> dict | None:
    """Scrape the (English) astrosage page for this sign/period, upsert the raw
    row (plus any deep-dive sections), and return the stored English row."""
    url = build_url(sign, period)
    html = await fetch_page(
        url, scope="horoscope", ref_id=sign, language="en", force=force,
    )
    parsed = parse_horoscope(html, url, sign=sign, period=period, language="en")
    _upsert(parsed, key)
    # The daily page also carries sign-level evergreen sections; harvest
    # them into zodiac_signs so /v1/reference/zodiac-signs/{id} has them
    # without a second fetch.
    if parsed.sign_deepdive is not None:
        _upsert_deepdive(parsed.sign_deepdive)
    return _select(sign, period, "en", key)


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
    Return one horoscope row as a plain dict.

    The astrosage source is English-only, so scraping ALWAYS targets the
    English page. Cleaning + translation into the other 11 languages happens
    via a single combined LLM call, kicked off in the background after the raw
    row is stored — the request never blocks on the LLM.

      - language == "en": serve cached, else (current period) scrape raw and
        return immediately; a background clean+translate upgrades the cache.
      - language != "en": serve cached translation if present; otherwise never
        scrape a *mislabelled* translation — ensure the English source exists,
        trigger the background pipeline, and fall back to the English row for
        this request (the requested language appears on a later request).
      - Past/future periods return None on miss so the caller can 404.

    `force=True` re-scrapes even if cached — useful for admin re-runs after
    parser improvements.
    """
    if sign not in SIGNS:
        raise ValueError(f"Unknown sign: {sign!r}")
    if period not in URL_TEMPLATES:
        raise ValueError(f"Unknown period: {period!r}")

    key = period_key(period, d)
    is_current = key == current_period_key(period, tz)

    if not force:
        cached = _select(sign, period, language, key)
        if cached is not None:
            # Self-heal: a raw English row whose background clean job never
            # completed (e.g. an earlier spin-down) gets re-triggered on access.
            if language == "en" and cached.get("llm_cleaned_at") is None and is_current:
                _schedule_clean_translate(sign, period, key, cached)
            return cached

    # --- English path -----------------------------------------------------
    if language == "en":
        if not force and not is_current:
            return None  # archive miss — caller should 404
        en_row = await _scrape_en(sign, period, key, force=force)
        if en_row is not None:
            _schedule_clean_translate(sign, period, key, en_row)
        return en_row

    # --- Non-English path -------------------------------------------------
    # No cached translation. Make sure we have an English source to translate
    # from, then trigger the pipeline and fall back to English for this call.
    en_row = _select(sign, period, "en", key)
    if en_row is None:
        if not is_current:
            return None  # archive miss — nothing to scrape or translate
        en_row = await _scrape_en(sign, period, key, force=force)
    if en_row is None:
        return None
    _schedule_clean_translate(sign, period, key, en_row)
    return en_row  # honest English fallback; translation arrives on a later request


# ---------------------------------------------------------------------------
# Stale-row cleanup
# ---------------------------------------------------------------------------

def cleanup_stale_horoscopes(tz: str = "Asia/Kolkata") -> dict:
    """Delete horoscope_predictions rows whose period_key is before the
    current calendar window for that period type.

    Period-key formats and stale condition:
      daily / tomorrow  → YYYY-MM-DD  < today  /  < tomorrow
      weekly / w_love   → YYYY-Wnn    < current ISO week
      monthly / n_month → YYYY-MM     < current month  /  < next month
      yearly            → YYYY        < current year
    """
    today = datetime.now(ZoneInfo(tz)).date()
    tomorrow = today + timedelta(days=1)
    iso_year, iso_week, _ = today.isocalendar()

    cutoffs: dict[str, str] = {
        "daily":       today.isoformat(),
        "tomorrow":    tomorrow.isoformat(),
        "weekly":      f"{iso_year:04d}-W{iso_week:02d}",
        "weekly_love": f"{iso_year:04d}-W{iso_week:02d}",
        "monthly":     f"{today.year:04d}-{today.month:02d}",
        "next_month":  f"{_add_months(today, 1).year:04d}-{_add_months(today, 1).month:02d}",
        "yearly":      f"{today.year:04d}",
    }

    total_deleted = 0
    conn = connect_rw()
    try:
        for period, cutoff in cutoffs.items():
            cur = conn.execute(
                "DELETE FROM horoscope_predictions WHERE period=%s AND period_key<%s",
                (period, cutoff),
            )
            total_deleted += cur.rowcount or 0
        conn.commit()
    finally:
        conn.close()

    return {"deleted": total_deleted, "tz": tz, "cutoffs": cutoffs}
