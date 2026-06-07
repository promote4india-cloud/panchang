"""
Horoscope endpoints (endpoints.md §6).

  GET /v1/horoscope/{sign}?period=...&date=YYYY-MM-DD&language=en&tz=Asia/Kolkata

Single endpoint, period-driven. Periods cover the seven scrapeable
astrosage templates (daily, tomorrow, weekly, weekly_love, monthly,
next_month, yearly). On a cache miss for the CURRENT period_key the
service fetches + parses + persists the corresponding astrosage page;
subsequent reads come straight from SQLite.
"""

from __future__ import annotations

from datetime import date as Date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response

from backend.auth import require_user
from backend.services.cache import DEFAULT_CACHE_CONTROL
from backend.services.horoscope import (
    PERIODS,
    SIGNS,
    Period,
    get_horoscope,
)
from backend.services.zodiac import get_zodiac_sign

router = APIRouter(
    prefix="/v1/horoscope",
    tags=["horoscope"],
    dependencies=[Depends(require_user)],
)

SignPath = Path(
    ...,
    pattern=r"^(aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)$",
    description="Zodiac sign (lowercase English).",
)
PeriodQ = Query(
    "daily",
    pattern=r"^(daily|tomorrow|weekly|weekly_love|monthly|next_month|yearly)$",
    description=(
        "Time window. 'daily'/'tomorrow' return a single-paragraph "
        "prediction; 'weekly'/'weekly_love' a one-paragraph weekly card; "
        "'monthly'/'next_month'/'yearly' a structured article with "
        "general/career/finance/health/love/family/advice sections."
    ),
)
LangQ = Query("en", min_length=2, max_length=5)
TzQ = Query("Asia/Kolkata")


@router.get("/{sign}")
async def horoscope(
    response: Response,
    sign: str = SignPath,
    period: Period = PeriodQ,
    date: Date | None = Query(
        None,
        description=(
            "Date the prediction should cover. Defaults to 'today' in "
            "`tz`. The period_key bucketing this request (day for daily, "
            "ISO week for weekly, etc.) is computed from this date."
        ),
    ),
    language: str = LangQ,
    tz: str = TzQ,
    include: bool = Query(
        False,
        description=(
            "When true, embeds a `zodiac` object with the sign's deep "
            "generalised info: structural fields (name, vedic_name, "
            "symbol, date_range, lord, element), sign_intro prose "
            "(summary, traits, love, compatibility), and deep-dive "
            "(overview, physical_appearance, mental_ability, "
            "characteristics, aspects_of_life, twelve_houses). Default "
            "false keeps the response lean."
        ),
    ),
    force: bool = Query(
        False,
        description=(
            "Bypass the DB cache and re-scrape from astrosage. Useful "
            "after a parser upgrade. Respects the 1 req/s polite throttle."
        ),
    ),
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    d = date or datetime.now(ZoneInfo(tz)).date()
    try:
        row = await get_horoscope(
            sign=sign, period=period, d=d,
            language=language, tz=tz, force=force,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if row is None:
        raise HTTPException(
            404,
            f"No archived horoscope for {sign}/{period} at period_key "
            f"derived from {d.isoformat()}. Astrosage does not expose past "
            f"periods; only the current bucket can be fetched on demand.",
        )

    body: dict = {
        "sign": row["sign"],
        "period": row["period"],
        "period_key": row["period_key"],
        "date": d.isoformat(),
        "date_label": row["date_label"],
        "language": row["language"],
        "prediction": row["prediction"],
        "ratings": row["ratings"],
        "categories": {
            "love": row["love"],
            "career": row["career"],
            "finance": row["finance"],
            "health": row["health"],
            "family": row["family"],
        },
        "advice": row["advice"],
        "source_url": row["source_url"],
        "scraped_at": row["scraped_at"],
    }

    if include:
        zodiac_obj = await get_zodiac_sign(sign_id=sign, language=language, force=force)
        if zodiac_obj is not None:
            body["zodiac"] = zodiac_obj
    return body


@router.get("")
def list_signs(response: Response):
    """Catalog endpoint — useful for clients to discover supported (sign, period) pairs."""
    response.headers["Cache-Control"] = "public, max-age=86400, immutable"
    return {
        "signs": list(SIGNS),
        "periods": list(PERIODS),
    }
