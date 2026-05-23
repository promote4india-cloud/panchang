"""
Public festivals endpoints (matches endpoints.md §5).

  GET /v1/festivals             — list in [from,to]
  GET /v1/festivals/today       — festival(s) today
  GET /v1/festivals/upcoming    — next 7d / 30d / 90d groupings
  GET /v1/festivals/calendar    — month grid
  GET /v1/festivals/{id}        — full editorial detail
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date as Date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Response

from backend.services.cache import DEFAULT_CACHE_CONTROL
from backend.services.db import connect_ro
from backend.services.festivals import festivals_in_range

router = APIRouter(prefix="/v1/festivals", tags=["festivals"])

LangQ = Query("en", min_length=2, max_length=5)
LatQ = Query(28.6139, ge=-90, le=90)
LonQ = Query(77.2090, ge=-180, le=180)
TzQ = Query("Asia/Kolkata")


@router.get("")
def list_festivals(
    response: Response,
    from_: Date | None = Query(None, alias="from"),
    to: Date | None = Query(None),
    type: str | None = Query(None),
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    today = datetime.now(ZoneInfo(tz)).date()
    if from_ is None:
        from_ = today.replace(day=1)
    if to is None:
        last_day = monthrange(from_.year, from_.month)[1]
        to = from_.replace(day=last_day)

    occ = festivals_in_range(from_, to, language=language, lat=lat, lon=lon, tz=tz)
    if type:
        occ = [o for o in occ if (o.type or "") == type]
    return [
        {
            "id": o.festival_id,
            "name": o.name,
            "date": o.date.isoformat(),
            "weekday": o.date.strftime("%a"),
            "type": o.type,
            "auspiciousness": o.auspiciousness,
        }
        for o in occ
    ]


@router.get("/today")
def today_festivals(
    response: Response,
    date: Date | None = Query(None),
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    today = date or datetime.now(ZoneInfo(tz)).date()
    occ = festivals_in_range(today, today, language=language, lat=lat, lon=lon, tz=tz)
    return {"festivals": [
        {"id": o.festival_id, "name": o.name, "type": o.type}
        for o in occ
    ]}


@router.get("/upcoming")
def upcoming(
    response: Response,
    from_: Date | None = Query(None, alias="from"),
    window: Literal["7d", "30d", "90d"] = Query("30d"),
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    start = from_ or datetime.now(ZoneInfo(tz)).date()
    days = {"7d": 7, "30d": 30, "90d": 90}[window]
    end = start + timedelta(days=days)
    occ = festivals_in_range(start, end, language=language, lat=lat, lon=lon, tz=tz)
    return {"items": [
        {
            "date": o.date.isoformat(),
            "weekday": o.date.strftime("%a").upper(),
            "id": o.festival_id,
            "name": o.name,
            "type": o.type,
        }
        for o in occ
    ]}


@router.get("/calendar")
def calendar(
    response: Response,
    year: int = Query(..., ge=1900, le=2100),
    month: int = Query(..., ge=1, le=12),
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    last = monthrange(year, month)[1]
    start = Date(year, month, 1)
    end = Date(year, month, last)
    occ = festivals_in_range(start, end, language=language, lat=lat, lon=lon, tz=tz)
    by_day: dict[int, list[dict]] = {}
    for o in occ:
        by_day.setdefault(o.date.day, []).append(
            {"id": o.festival_id, "name": o.name, "type": o.type}
        )
    return {
        "year": year, "month": month,
        "days": [
            {
                "day": d,
                "weekday": Date(year, month, d).strftime("%a").upper(),
                "events": by_day.get(d, []),
            }
            for d in range(1, last + 1)
        ],
    }


@router.get("/{festival_id}/dates")
def festival_dates(
    festival_id: str,
    response: Response,
    year: int = Query(..., ge=1900, le=2100),
    include_children: bool = Query(
        True,
        description="Include child/variant festivals (e.g. Diwali → Dhanteras, Govardhan, Bhai Dooj).",
    ),
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
):
    """All occurrences of a festival (and its variants) in the given year.

    Useful for monthly festivals (Masik Shivaratri → 12 dates, Sankashti
    Chaturthi → 12-13 dates, Ekadashi → 24-26 dates) and for festival
    families with sub-events (Diwali → Dhanteras, Narak Chaturdashi,
    Lakshmi Puja, Govardhan Puja, Bhai Dooj).
    """
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL

    # Collect the festival_id plus, optionally, every descendant. We walk
    # by `slug_path` prefix (more reliable than `parent_id`, which is not
    # always populated on imported rows).
    conn = connect_ro()
    try:
        root = conn.execute(
            "SELECT id, slug_path FROM festivals WHERE id = ?", (festival_id,)
        ).fetchone()
        if not root:
            raise HTTPException(404, f"Unknown festival: {festival_id}")
        ids: set[str] = {festival_id}
        if include_children:
            prefix = root["slug_path"] + "/"
            for r in conn.execute(
                "SELECT id FROM festivals WHERE slug_path LIKE ?", (prefix + "%",),
            ).fetchall():
                ids.add(r["id"])
    finally:
        conn.close()

    start = Date(year, 1, 1)
    end = Date(year, 12, 31)
    occ = festivals_in_range(start, end, language=language, lat=lat, lon=lon, tz=tz)
    occ = [o for o in occ if o.festival_id in ids]

    grouped: dict[str, list[dict]] = {}
    for o in occ:
        grouped.setdefault(o.festival_id, []).append(
            {
                "date": o.date.isoformat(),
                "weekday": o.date.strftime("%a"),
                "name": o.name,
            }
        )

    return {
        "festival_id": festival_id,
        "year": year,
        "include_children": include_children,
        "variants": [
            {
                "id": fid,
                "name": dates[0]["name"] if dates else fid,
                "count": len(dates),
                "dates": [{"date": d["date"], "weekday": d["weekday"]} for d in dates],
            }
            for fid, dates in sorted(grouped.items())
        ],
        "total": sum(len(v) for v in grouped.values()),
    }


@router.get("/{festival_id}")
def festival_detail(festival_id: str, response: Response, language: str = LangQ):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    conn = connect_ro()
    try:
        f = conn.execute(
            "SELECT * FROM festivals WHERE id = ?", (festival_id,)
        ).fetchone()
        if not f:
            raise HTTPException(404, f"Unknown festival: {festival_id}")
        c = conn.execute(
            "SELECT * FROM festival_content WHERE festival_id = ? AND language = ?",
            (festival_id, language),
        ).fetchone() or conn.execute(
            "SELECT * FROM festival_content WHERE festival_id = ? AND language = 'en'",
            (festival_id,),
        ).fetchone()
        rituals = [
            r["text"] for r in conn.execute(
                """SELECT text FROM festival_rituals
                   WHERE festival_id = ? AND language = ?
                   ORDER BY position""",
                (festival_id, language),
            ).fetchall()
        ]
        faqs = [
            {"question": r["question"], "answer": r["answer"]}
            for r in conn.execute(
                """SELECT question, answer FROM festival_faqs
                   WHERE festival_id = ? AND language = ?
                   ORDER BY position""",
                (festival_id, language),
            ).fetchall()
        ]
    finally:
        conn.close()

    return {
        "id": f["id"],
        "slug_path": f["slug_path"],
        "parent_id": f["parent_id"],
        "kind": f["kind"],
        "type": f["type"],
        "auspiciousness": f["auspiciousness"],
        "thumbnail_url": f["thumbnail_url"],
        "rule": {"type": f["rule_type"], "json": f["rule_json"]},
        "content": dict(c) if c else None,
        "rituals": rituals,
        "faqs": faqs,
    }
