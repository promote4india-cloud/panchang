"""
Public festivals endpoints (matches endpoints.md Â§5).

  GET /v1/festivals             â€” list in [from,to]
  GET /v1/festivals/today       â€” festival(s) today
  GET /v1/festivals/upcoming    â€” next 7d / 30d / 90d groupings
  GET /v1/festivals/calendar    â€” month grid
  GET /v1/festivals/{id}        â€” full editorial detail
"""

from __future__ import annotations

import json
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
TraditionQ = Query(
    "all",
    description=(
        "Filter occurrences by lunar-month naming convention or region. "
        "Direct values: 'all' (default), 'purnimanta', 'amanta'. "
        "Direction aliases: 'north', 'south', 'east', 'west', 'central', "
        "'northeast', 'northwest'. State aliases: 'bengal', 'odisha', "
        "'maharashtra', 'gujarat', 'karnataka', 'tamil-nadu', 'kerala', "
        "etc. Aliases resolve to the underlying tradition(s); festivals "
        "tagged with either are returned. Comma-separate to union multiple "
        "regions (e.g. 'north,west')."
    ),
)
AyanamsaQ = Query(
    "lahiri",
    description=(
        "Sidereal ayanamsa frame for tithi/nakshatra/rashi calculations. "
        "Default 'lahiri' = Indian Govt / Drik convention. Other modes: "
        "'surya_siddhanta' (Bangladesh / classical Panjika), 'raman' "
        "(B.V. Raman), 'krishnamurti' (KP astrology), 'true_citra' "
        "(Drik Chitra-paksha refinement), 'yukteshwar', 'fagan_bradley' "
        "(Western sidereal). Affects sankranti boundaries (and hence "
        "regional new-year dates) by 0-1 day across years."
    ),
)
CalendarTimeQ = Query(
    "civil",
    description=(
        "Time reference for sunrise/sunset anchors. 'civil' (default) "
        "uses the supplied IANA tz. 'LMT' uses Local Mean Time "
        "(longitude * 4 min/deg), matching classical panjika reckoning. "
        "LMT can shift sunrise by up to ~30 min vs IST in extreme east/west "
        "Indian longitudes, occasionally flipping a sunrise-anchored "
        "festival by one day."
    ),
)


# Region / community / sect -> equivalence bag of tradition tags. A caller
# value is expanded into ALL its synonyms; a festival passes the filter if
# either (a) its scope_traditions intersects the bag, OR (b) the festival
# is universal (empty scope) -- AND for occurrences with variant tags from
# `multi_tradition` rules, the variant set must also intersect (so e.g.
# `tradition=kerala` collapses Janmashtami to the Amanta/Smarta dates).
#
# The bag mixes axes deliberately: a state expands to its language(s),
# region direction, calendar convention, and (where exclusive) sect, so
# the single intersection check covers all four axes at once.
#
# Unknown values pass through verbatim so adding a new tag in SCOPES does
# not require touching this map.
REGION_TRADITIONS: dict[str, list[str]] = {
    "all":         [],
    "any":         [],
    "":            [],

    # ---- Calendar conventions (variant axis) ----
    "purnimanta":  ["purnimanta"],
    "amanta":      ["amanta"],

    # ---- Devotional schools / sects ----
    "smarta":      ["smarta"],
    "vaishnava":   ["vaishnava"],
    "iskcon":      ["vaishnava"],
    "shaiva":      ["shaiva"],
    "shakta":      ["shakta"],
    "jain":        ["jain"],
    "sikh":        ["sikh", "punjab", "punjabi", "north", "purnimanta"],
    "buddhist":    ["buddhist"],
    "brahmin":     ["brahmin"],
    "muslim":      ["muslim", "islamic"],
    "islamic":     ["islamic", "muslim"],
    "shia":        ["shia", "muslim", "islamic"],
    "sunni":       ["sunni", "muslim", "islamic"],
    "bangladesh":  ["bangladesh", "bengali", "east"],

    # ---- Cardinal directions ----
    "north":     ["north", "purnimanta"],
    "northwest": ["northwest", "north", "purnimanta"],
    "northeast": ["northeast", "east", "purnimanta"],
    "east":      ["east", "purnimanta"],
    "central":   ["central", "purnimanta"],
    "south":     ["south", "amanta"],
    "west":      ["west", "amanta"],
    "southwest": ["southwest", "west", "amanta"],
    "southeast": ["southeast", "south", "amanta"],

    # ---- Language communities (deliberately overlap with states) ----
    "tamil":     ["tamil", "tamil-nadu", "south", "amanta"],
    "malayali":  ["malayali", "kerala", "south", "amanta"],
    "telugu":    ["telugu", "andhra-pradesh", "telangana", "south", "amanta"],
    "kannada":   ["kannada", "karnataka", "south", "amanta"],
    "marathi":   ["marathi", "maharashtra", "konkani", "west", "amanta"],
    "konkani":   ["konkani", "goa", "maharashtra", "west", "amanta"],
    "gujarati":  ["gujarati", "gujarat", "west", "amanta"],
    "sindhi":    ["sindhi"],
    "punjabi":   ["punjabi", "punjab", "sikh", "north", "purnimanta"],
    "bengali":   ["bengali", "bengal", "west-bengal", "east", "purnimanta"],
    "oriya":     ["oriya", "odia", "odisha", "east", "purnimanta"],
    "odia":      ["odia", "oriya", "odisha", "east", "purnimanta"],
    "assamese":  ["assamese", "assam", "northeast", "east", "purnimanta"],
    "bhojpuri":  ["bhojpuri", "bihar", "purvanchal", "east", "purnimanta"],
    "maithili":  ["maithili", "bihar", "east", "purnimanta"],

    # ---- Sub-regions ----
    "purvanchal": ["purvanchal", "bihar", "jharkhand", "up",
                   "uttar-pradesh", "east", "purnimanta"],

    # ---- Purnimanta states (North / East / parts of Central) ----
    "bengal":          ["bengal", "west-bengal", "bengali", "east", "purnimanta"],
    "west-bengal":     ["west-bengal", "bengal", "bengali", "east", "purnimanta"],
    "westbengal":      ["west-bengal", "bengal", "bengali", "east", "purnimanta"],
    "odisha":          ["odisha", "oriya", "odia", "east", "purnimanta"],
    "orissa":          ["odisha", "oriya", "odia", "east", "purnimanta"],
    "assam":           ["assam", "assamese", "northeast", "east", "purnimanta"],
    "bihar":           ["bihar", "bhojpuri", "maithili", "purvanchal",
                        "east", "purnimanta"],
    "jharkhand":       ["jharkhand", "east", "purnimanta"],
    "up":              ["up", "uttar-pradesh", "bhojpuri", "purvanchal",
                        "north", "purnimanta"],
    "uttar-pradesh":   ["uttar-pradesh", "up", "bhojpuri", "purvanchal",
                        "north", "purnimanta"],
    "uttarpradesh":    ["uttar-pradesh", "up", "north", "purnimanta"],
    "uttarakhand":     ["uttarakhand", "north", "purnimanta"],
    "delhi":           ["delhi", "north", "purnimanta"],
    "haryana":         ["haryana", "north", "purnimanta"],
    "punjab":          ["punjab", "punjabi", "sikh", "north", "purnimanta"],
    "himachal":        ["himachal", "himachal-pradesh", "north", "purnimanta"],
    "himachal-pradesh":["himachal-pradesh", "himachal", "north", "purnimanta"],
    "jammu":           ["jammu", "kashmir", "north", "purnimanta"],
    "kashmir":         ["kashmir", "jammu", "north", "purnimanta"],
    "rajasthan":       ["rajasthan", "north", "purnimanta"],
    "mp":              ["mp", "madhya-pradesh", "central", "purnimanta"],
    "madhya-pradesh":  ["madhya-pradesh", "mp", "central", "purnimanta"],
    "madhyapradesh":   ["madhya-pradesh", "mp", "central", "purnimanta"],
    "chhattisgarh":    ["chhattisgarh", "central", "purnimanta"],
    "sikkim":          ["sikkim", "northeast", "east", "purnimanta"],
    "manipur":         ["manipur", "northeast", "east", "purnimanta"],
    "tripura":         ["tripura", "northeast", "east", "purnimanta"],
    "meghalaya":       ["meghalaya", "northeast", "east", "purnimanta"],
    "nagaland":        ["nagaland", "northeast", "east", "purnimanta"],
    "arunachal":       ["arunachal", "northeast", "east", "purnimanta"],
    "mizoram":         ["mizoram", "northeast", "east", "purnimanta"],

    # ---- Amanta states (South / West) ----
    "maharashtra":    ["maharashtra", "marathi", "konkani", "west", "amanta"],
    "gujarat":        ["gujarat", "gujarati", "west", "amanta"],
    "goa":            ["goa", "konkani", "marathi", "west", "amanta"],
    "karnataka":      ["karnataka", "kannada", "south", "amanta"],
    "andhra":         ["andhra-pradesh", "telugu", "south", "amanta"],
    "andhra-pradesh": ["andhra-pradesh", "telugu", "south", "amanta"],
    "andhrapradesh":  ["andhra-pradesh", "telugu", "south", "amanta"],
    "telangana":      ["telangana", "telugu", "south", "amanta"],
    "tamil-nadu":     ["tamil-nadu", "tamil", "south", "amanta"],
    "tamilnadu":      ["tamil-nadu", "tamil", "south", "amanta"],
    "tamilnadu-tn":   ["tamil-nadu", "tamil", "south", "amanta"],
    "kerala":         ["kerala", "malayali", "south", "amanta"],
}


def _scope_vocabulary() -> set[str]:
    """Union of every tag the router knows how to resolve to. Used by the
    boot-time validator to flag SCOPES entries with tags no caller could
    ever query for (typos, vocabulary drift).
    """
    vocab: set[str] = set(REGION_TRADITIONS.keys())
    for v in REGION_TRADITIONS.values():
        vocab.update(v)
    return vocab


def validate_scope_vocabulary() -> dict[str, list[str]]:
    """Cross-check the curated SCOPES map (in services/festival_rules_seed.py)
    against the router's resolvable vocabulary. Returns a dict mapping
    festival id -> list of unknown tags. Empty dict means clean.

    Logs a WARNING for any unknown tag so vocabulary drift surfaces in
    server logs at startup. Does NOT raise -- unknown tags still work
    (the resolver passes them through verbatim) but a caller would have
    to know the exact tag string to query for them.
    """
    import logging

    try:
        from backend.services.festival_rules_seed import SCOPES
    except Exception as exc:  # pragma: no cover - defensive
        logging.warning("scope validator: could not import SCOPES (%s)", exc)
        return {}

    vocab = _scope_vocabulary()
    unknown: dict[str, list[str]] = {}
    for fid, tags in SCOPES.items():
        missing = [t for t in tags if t not in vocab]
        if missing:
            unknown[fid] = missing
    if unknown:
        for fid, missing in sorted(unknown.items()):
            logging.warning(
                "scope tag(s) not in router vocabulary for festival %r: %s",
                fid, ", ".join(missing),
            )
    return unknown


# Run validation at import time so the warnings show up on app boot.
try:
    validate_scope_vocabulary()
except Exception:  # pragma: no cover
    pass


def _resolve_tradition_tags(value: str) -> list[str]:
    """Resolve a tradition/region query value into a list of tradition tags.
    Empty list means "no filter" (return all occurrences). Unknown values are
    passed through verbatim so future tags work without code changes.
    """
    if not value:
        return []
    tags: list[str] = []
    for part in value.split(","):
        key = part.strip().lower().replace("_", "-")
        if not key:
            continue
        resolved = REGION_TRADITIONS.get(key)
        if resolved is None:
            tags.append(key)
        else:
            tags.extend(resolved)
    # Dedupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def _filter_tradition(occ, tradition: str):
    """Apply BOTH scope and variant filters using the same expanded tag bag.

    * SCOPE filter (festival-level): drop the occurrence if the festival's
      `scope_traditions` is non-empty and does not intersect the bag.
      Universal festivals (empty scope) always pass.
    * VARIANT filter (occurrence-level): drop the occurrence if its
      `traditions` tuple is non-empty and does not intersect the bag.
      Tradition-agnostic occurrences (empty variant) always pass.

    With `tradition=all` (or unset) the bag is empty and BOTH filters are
    bypassed -- every festival and every variant is returned.
    """
    tags = _resolve_tradition_tags(tradition or "all")
    if not tags:
        return occ
    bag = set(tags)
    return [
        o for o in occ
        if (not o.scope_traditions or bag.intersection(o.scope_traditions))
        and (not o.traditions or bag.intersection(o.traditions))
    ]


def _content_payload(row) -> dict:
    data = dict(row)
    data.pop("festival_id", None)
    data.pop("language", None)
    return data


def _fetch_festival_content(conn, festival_ids: list[str], language: str) -> dict[str, dict]:
    if not festival_ids:
        return {}
    placeholders = ",".join(["%s"] * len(festival_ids))
    rows = conn.execute(
        f"""
        SELECT * FROM festival_content
         WHERE festival_id IN ({placeholders})
           AND language = %s
        """,
        (*festival_ids, language),
    ).fetchall()
    content = {r["festival_id"]: _content_payload(r) for r in rows}
    if language != "en":
        missing = [fid for fid in festival_ids if fid not in content]
        if missing:
            placeholders = ",".join(["%s"] * len(missing))
            rows = conn.execute(
                f"""
                SELECT * FROM festival_content
                 WHERE festival_id IN ({placeholders})
                   AND language = 'en'
                """,
                (*missing,),
            ).fetchall()
            for r in rows:
                content.setdefault(r["festival_id"], _content_payload(r))
    return content


def _fetch_festival_rituals(conn, festival_ids: list[str], language: str) -> dict[str, list[str]]:
    if not festival_ids:
        return {}
    placeholders = ",".join(["%s"] * len(festival_ids))
    rows = conn.execute(
        f"""
        SELECT festival_id, text
          FROM festival_rituals
         WHERE festival_id IN ({placeholders})
           AND language = %s
         ORDER BY festival_id, position
        """,
        (*festival_ids, language),
    ).fetchall()
    rituals: dict[str, list[str]] = {}
    for row in rows:
        rituals.setdefault(row["festival_id"], []).append(row["text"])
    return rituals


def _fetch_festival_faqs(conn, festival_ids: list[str], language: str) -> dict[str, list[dict]]:
    if not festival_ids:
        return {}
    placeholders = ",".join(["%s"] * len(festival_ids))
    rows = conn.execute(
        f"""
        SELECT festival_id, question, answer
          FROM festival_faqs
         WHERE festival_id IN ({placeholders})
           AND language = %s
         ORDER BY festival_id, position
        """,
        (*festival_ids, language),
    ).fetchall()
    faqs: dict[str, list[dict]] = {}
    for row in rows:
        faqs.setdefault(row["festival_id"], []).append(
            {"question": row["question"], "answer": row["answer"]}
        )
    return faqs


@router.get("")
def list_festivals(
    response: Response,
    from_: Date | None = Query(None, alias="from"),
    to: Date | None = Query(None),
    type: str | None = Query(None),
    tradition: str = TraditionQ,
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
    ayanamsa: str = AyanamsaQ,
    calendar_time: str = CalendarTimeQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    today = datetime.now(ZoneInfo(tz)).date()
    if from_ is None:
        from_ = today.replace(day=1)
    if to is None:
        last_day = monthrange(from_.year, from_.month)[1]
        to = from_.replace(day=last_day)

    occ = festivals_in_range(from_, to, language=language, lat=lat, lon=lon, tz=tz, ayanamsa=ayanamsa, calendar_time=calendar_time)
    occ = _filter_tradition(occ, tradition)
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
            "traditions": list(o.traditions),
            "scope_traditions": list(o.scope_traditions),
            "adhik_status": o.adhik_status,
            "kshaya_label": o.kshaya_label,
            "kollam_year": o.kollam_year,
            "tamil_year": o.tamil_year,
            "puja_muhurats": [m.to_dict() for m in o.puja_muhurats],
            "primary": o.primary,
        }
        for o in occ
    ]


@router.get("/today")
def today_festivals(
    response: Response,
    date: Date | None = Query(None),
    tradition: str = TraditionQ,
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
    ayanamsa: str = AyanamsaQ,
    calendar_time: str = CalendarTimeQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    today = date or datetime.now(ZoneInfo(tz)).date()
    occ = festivals_in_range(today, today, language=language, lat=lat, lon=lon, tz=tz, ayanamsa=ayanamsa, calendar_time=calendar_time)
    occ = _filter_tradition(occ, tradition)
    return {"festivals": [
        {"id": o.festival_id, "name": o.name, "type": o.type,
         "traditions": list(o.traditions),
         "scope_traditions": list(o.scope_traditions),
         "adhik_status": o.adhik_status,
         "kshaya_label": o.kshaya_label,
         "puja_muhurats": [m.to_dict() for m in o.puja_muhurats],
         "primary": o.primary}
        for o in occ
    ]}


@router.get("/upcoming")
def upcoming(
    response: Response,
    from_: Date | None = Query(None, alias="from"),
    window: Literal["7d", "30d", "90d"] = Query("30d"),
    tradition: str = TraditionQ,
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
    ayanamsa: str = AyanamsaQ,
    calendar_time: str = CalendarTimeQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    start = from_ or datetime.now(ZoneInfo(tz)).date()
    days = {"7d": 7, "30d": 30, "90d": 90}[window]
    end = start + timedelta(days=days)
    occ = festivals_in_range(start, end, language=language, lat=lat, lon=lon, tz=tz, ayanamsa=ayanamsa, calendar_time=calendar_time)
    occ = _filter_tradition(occ, tradition)
    return {"items": [
        {
            "date": o.date.isoformat(),
            "weekday": o.date.strftime("%a").upper(),
            "id": o.festival_id,
            "name": o.name,
            "type": o.type,
            "traditions": list(o.traditions),
            "scope_traditions": list(o.scope_traditions),
            "adhik_status": o.adhik_status,
            "puja_muhurats": [m.to_dict() for m in o.puja_muhurats],
            "primary": o.primary,
        }
        for o in occ
    ]}


@router.get("/calendar")
def calendar(
    response: Response,
    year: int = Query(..., ge=1900, le=2100),
    month: int = Query(..., ge=1, le=12),
    tradition: str = TraditionQ,
    language: str = LangQ,
    include_content: bool = Query(
        False,
        description="Include editorial content, rituals, and FAQs for each festival.",
    ),
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
    ayanamsa: str = AyanamsaQ,
    calendar_time: str = CalendarTimeQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    last = monthrange(year, month)[1]
    start = Date(year, month, 1)
    end = Date(year, month, last)
    occ = festivals_in_range(start, end, language=language, lat=lat, lon=lon, tz=tz, ayanamsa=ayanamsa, calendar_time=calendar_time)
    occ = _filter_tradition(occ, tradition)
    content_map: dict[str, dict] = {}
    rituals_map: dict[str, list[str]] = {}
    faqs_map: dict[str, list[dict]] = {}
    if include_content and occ:
        festival_ids = sorted({o.festival_id for o in occ})
        conn = connect_ro()
        try:
            content_map = _fetch_festival_content(conn, festival_ids, language)
            rituals_map = _fetch_festival_rituals(conn, festival_ids, language)
            faqs_map = _fetch_festival_faqs(conn, festival_ids, language)
        finally:
            conn.close()
    by_day: dict[int, list[dict]] = {}
    for o in occ:
        item = {
            "id": o.festival_id,
            "name": o.name,
            "type": o.type,
            "traditions": list(o.traditions),
            "scope_traditions": list(o.scope_traditions),
            "adhik_status": o.adhik_status,
            "puja_muhurats": [m.to_dict() for m in o.puja_muhurats],
            "primary": o.primary,
        }
        if include_content:
            item["content"] = content_map.get(o.festival_id)
            item["rituals"] = rituals_map.get(o.festival_id, [])
            item["faqs"] = faqs_map.get(o.festival_id, [])
        by_day.setdefault(o.date.day, []).append(item)
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
        description="Include child/variant festivals (e.g. Diwali â†’ Dhanteras, Govardhan, Bhai Dooj).",
    ),
    tradition: str = TraditionQ,
    language: str = LangQ,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
    ayanamsa: str = AyanamsaQ,
    calendar_time: str = CalendarTimeQ,
):
    """All occurrences of a festival (and its variants) in the given year.

    Useful for monthly festivals (Masik Shivaratri â†’ 12 dates, Sankashti
    Chaturthi â†’ 12-13 dates, Ekadashi â†’ 24-26 dates) and for festival
    families with sub-events (Diwali â†’ Dhanteras, Narak Chaturdashi,
    Lakshmi Puja, Govardhan Puja, Bhai Dooj).
    """
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL

    # Collect the festival_id plus, optionally, every descendant. We walk
    # by `slug_path` prefix (more reliable than `parent_id`, which is not
    # always populated on imported rows).
    conn = connect_ro()
    try:
        root = conn.execute(
            "SELECT id, slug_path FROM festivals WHERE id = %s", (festival_id,)
        ).fetchone()
        if not root:
            raise HTTPException(404, f"Unknown festival: {festival_id}")
        ids: set[str] = {festival_id}
        if include_children:
            prefix = root["slug_path"] + "/"
            for r in conn.execute(
                "SELECT id FROM festivals WHERE slug_path LIKE %s", (prefix + "%",),
            ).fetchall():
                ids.add(r["id"])
    finally:
        conn.close()

    start = Date(year, 1, 1)
    end = Date(year, 12, 31)
    occ = festivals_in_range(start, end, language=language, lat=lat, lon=lon, tz=tz, ayanamsa=ayanamsa, calendar_time=calendar_time)
    occ = _filter_tradition(occ, tradition)
    occ = [o for o in occ if o.festival_id in ids]

    grouped: dict[str, list[dict]] = {}
    for o in occ:
        grouped.setdefault(o.festival_id, []).append(
            {
                "date": o.date.isoformat(),
                "weekday": o.date.strftime("%a"),
                "name": o.name,
                "traditions": list(o.traditions),
                "scope_traditions": list(o.scope_traditions),
                "adhik_status": o.adhik_status,
                "kshaya_label": o.kshaya_label,
                "puja_muhurats": [m.to_dict() for m in o.puja_muhurats],
                "primary": o.primary,
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
                "scope_traditions": dates[0]["scope_traditions"] if dates else [],
                "dates": [
                    {
                        "date": d["date"],
                        "weekday": d["weekday"],
                        "traditions": d["traditions"],
                        "adhik_status": d["adhik_status"],
                        "kshaya_label": d["kshaya_label"],
                        "puja_muhurats": d["puja_muhurats"],
                        "primary": d["primary"],
                    }
                    for d in dates
                ],
            }
            for fid, dates in sorted(grouped.items())
        ],
        "total": sum(len(v) for v in grouped.values()),
    }


@router.get("/{festival_id}")
def festival_detail(
    festival_id: str,
    response: Response,
    language: str = LangQ,
    date: Date | None = Query(
        None,
        description=(
            "Optional civil date to compute puja_muhurats for this "
            "festival. When omitted, response contains only editorial "
            "content (no muhurat windows)."
        ),
    ),
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
    ayanamsa: str = AyanamsaQ,
    calendar_time: str = CalendarTimeQ,
):
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    conn = connect_ro()
    try:
        f = conn.execute(
            "SELECT * FROM festivals WHERE id = %s", (festival_id,)
        ).fetchone()
        if not f:
            raise HTTPException(404, f"Unknown festival: {festival_id}")
        c = conn.execute(
            "SELECT * FROM festival_content WHERE festival_id = %s AND language = %s",
            (festival_id, language),
        ).fetchone() or conn.execute(
            "SELECT * FROM festival_content WHERE festival_id = %s AND language = 'en'",
            (festival_id,),
        ).fetchone()
        rituals = [
            r["text"] for r in conn.execute(
                """SELECT text FROM festival_rituals
                   WHERE festival_id = %s AND language = %s
                   ORDER BY position""",
                (festival_id, language),
            ).fetchall()
        ]
        faqs = [
            {"question": r["question"], "answer": r["answer"]}
            for r in conn.execute(
                """SELECT question, answer FROM festival_faqs
                   WHERE festival_id = %s AND language = %s
                   ORDER BY position""",
                (festival_id, language),
            ).fetchall()
        ]
    finally:
        conn.close()

    result = {
        "id": f["id"],
        "slug_path": f["slug_path"],
        "parent_id": f["parent_id"],
        "kind": f["kind"],
        "type": f["type"],
        "auspiciousness": f["auspiciousness"],
        "thumbnail_url": f["thumbnail_url"],
        "scope_traditions": json.loads(f["scope_traditions"]) if f["scope_traditions"] else [],
        "rule": {"type": f["rule_type"], "json": f["rule_json"]},
        "content": dict(c) if c else None,
        "rituals": rituals,
        "faqs": faqs,
    }
    if date is not None:
        # Resolve the festival's occurrence on (or nearest to) `date`
        # within ±45 days, then attach puja_muhurats.
        from datetime import timedelta
        window_start = date - timedelta(days=45)
        window_end = date + timedelta(days=45)
        occ_window = festivals_in_range(
            window_start, window_end, language=language,
            lat=lat, lon=lon, tz=tz, ayanamsa=ayanamsa,
            calendar_time=calendar_time,
        )
        match = next(
            (o for o in occ_window if o.festival_id == festival_id and o.date == date),
            None,
        )
        if match is None:
            # Fall back to nearest occurrence within the window.
            same_id = [o for o in occ_window if o.festival_id == festival_id]
            if same_id:
                match = min(same_id, key=lambda o: abs((o.date - date).days))
        result["date"] = match.date.isoformat() if match else date.isoformat()
        result["puja_muhurats"] = (
            [m.to_dict() for m in match.puja_muhurats] if match else []
        )
    return result

