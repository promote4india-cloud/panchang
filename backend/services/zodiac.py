"""
Zodiac sign catalog — hybrid static + lazy-scraped editorial.

Two field classes:

  * Structural (evergreen): name, vedic_name, symbol, date_range, lord,
    element. These are Python constants here — single source of truth.

  * Prose (editorial): summary, traits, love, compatibility. Persisted in
    the `zodiac_signs` table per (id, language). Filled on first read
    from www.astrosage.com/horoscope/{id}.asp via parse_sign_intro.

`get_zodiac_sign(id, language)` returns a merged dict. The list helpers
(`zodiac_index`, `iter_zodiac_summary`) deal only with the structural side
so the existing `/v1/reference/zodiac-signs` catalog endpoint stays
network-free.
"""

from __future__ import annotations

from dataclasses import asdict

from .db import connect_ro, connect_rw
from .panchang import RASHI_LORDS, RASHI_NAMES
from .scraper import fetch_page
from .scraper.parsers.sign_intro import ParsedSignIntro, parse_sign_intro

HOST = "https://www.astrosage.com"

# Order matters — index 0 = Aries (rashi 1). Indexes line up with
# RASHI_NAMES / RASHI_LORDS so we can zip(...) downstream.
SIGN_IDS: tuple[str, ...] = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
SIGN_ID_SET = frozenset(SIGN_IDS)

# Western (English) name + tropical date range + Unicode glyph.
_WESTERN: tuple[tuple[str, str, str], ...] = (
    ("Aries",       "Mar 21 – Apr 19", "♈"),
    ("Taurus",      "Apr 20 – May 20", "♉"),
    ("Gemini",      "May 21 – Jun 20", "♊"),
    ("Cancer",      "Jun 21 – Jul 22", "♋"),
    ("Leo",         "Jul 23 – Aug 22", "♌"),
    ("Virgo",       "Aug 23 – Sep 22", "♍"),
    ("Libra",       "Sep 23 – Oct 22", "♎"),
    ("Scorpio",     "Oct 23 – Nov 21", "♏"),
    ("Sagittarius", "Nov 22 – Dec 21", "♐"),
    ("Capricorn",   "Dec 22 – Jan 19", "♑"),
    ("Aquarius",    "Jan 20 – Feb 18", "♒"),
    ("Pisces",      "Feb 19 – Mar 20", "♓"),
)

# Classical element cycle: Fire, Earth, Air, Water repeating.
_ELEMENTS: tuple[str, ...] = (
    "Fire", "Earth", "Air", "Water",
    "Fire", "Earth", "Air", "Water",
    "Fire", "Earth", "Air", "Water",
)


def _structural(index: int) -> dict:
    name, range_str, symbol = _WESTERN[index]
    return {
        "id": SIGN_IDS[index],
        "index": index + 1,
        "name": name,
        "vedic_name": RASHI_NAMES[index],
        "symbol": symbol,
        "date_range": range_str,
        "lord": RASHI_LORDS[index],
        "element": _ELEMENTS[index],
    }


def zodiac_index() -> list[dict]:
    """Structural catalog of all 12 signs — no DB, no network."""
    return [_structural(i) for i in range(12)]


def get_structural(sign_id: str) -> dict | None:
    if sign_id not in SIGN_ID_SET:
        return None
    return _structural(SIGN_IDS.index(sign_id))


# ---------------------------------------------------------------------------
# Prose layer — DB + lazy scrape from two source pages
# ---------------------------------------------------------------------------

# Prose fields filled by the sign-intro page (`/horoscope/{sign}.asp`):
_INTRO_COLS = ("summary", "traits", "love", "compatibility")

# Deep-dive fields filled by the daily horoscope page
# (`/horoscope/daily-{sign}-horoscope.asp`). The horoscope service writes
# these whenever a daily prediction is scraped; the zodiac service also
# triggers a daily fetch on miss so the detail endpoint is self-healing.
_DEEPDIVE_COLS = (
    "overview", "physical_appearance", "mental_ability",
    "characteristics", "aspects_of_life", "twelve_houses",
)

_PROSE_COLS = _INTRO_COLS + _DEEPDIVE_COLS


def _select_prose(sign_id: str, language: str) -> dict | None:
    conn = connect_ro()
    try:
        row = conn.execute(
            f"SELECT {', '.join(_PROSE_COLS)}, source_url, scraped_at "
            "FROM zodiac_signs WHERE id=%s AND language=%s",
            (sign_id, language),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return dict(row)


def _upsert_intro(parsed: ParsedSignIntro) -> None:
    """UPSERT just the sign-intro fields, preserving any deep-dive cols
    a prior daily-page scrape may have written via COALESCE."""
    conn = connect_rw()
    try:
        conn.execute(
            """
            INSERT INTO zodiac_signs (
                id, language, summary, traits, love, compatibility,
                source_url, scraped_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT(id, language) DO UPDATE SET
                summary       = COALESCE(excluded.summary,       zodiac_signs.summary),
                traits        = COALESCE(excluded.traits,        zodiac_signs.traits),
                love          = COALESCE(excluded.love,          zodiac_signs.love),
                compatibility = COALESCE(excluded.compatibility, zodiac_signs.compatibility),
                source_url    = excluded.source_url,
                scraped_at    = NOW()
            """,
            (
                parsed.sign, parsed.language, parsed.summary, parsed.traits,
                parsed.love, parsed.compatibility, parsed.source_url,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _missing_cols(row: dict | None, cols: tuple[str, ...]) -> bool:
    if not row:
        return True
    return any(not row.get(c) for c in cols)


async def get_zodiac_sign(
    *, sign_id: str, language: str = "en", force: bool = False,
) -> dict | None:
    """
    Merged structural + prose dict for one sign. Lazy-scrapes the
    sign-intro page (for summary/traits/love/compatibility) AND/OR the
    daily horoscope page (for overview/physical_appearance/...) as
    needed. Each page is fetched at most once per cache window per
    (sign, language) thanks to the shared scraped_pages cache.

    Returns None for unknown sign ids.
    """
    from .horoscope import get_horoscope  # local import: avoid cycle at module load

    structural = get_structural(sign_id)
    if structural is None:
        return None

    prose = None if force else _select_prose(sign_id, language)

    # Sign-intro page → summary/traits/love/compatibility
    if force or _missing_cols(prose, _INTRO_COLS):
        url = f"{HOST}/horoscope/{sign_id}.asp"
        html = await fetch_page(
            url, scope="horoscope", ref_id=sign_id,
            language=language, force=force,
        )
        parsed = parse_sign_intro(html, url, sign=sign_id, language=language)
        _upsert_intro(parsed)
        prose = _select_prose(sign_id, language)

    # Daily page → overview/physical_appearance/mental_ability/characteristics/
    # aspects_of_life/twelve_houses (the horoscope service persists these as
    # a side-effect of scraping today's prediction).
    if force or _missing_cols(prose, _DEEPDIVE_COLS):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        await get_horoscope(
            sign=sign_id, period="daily", d=today,
            language=language, tz="Asia/Kolkata", force=force,
        )
        prose = _select_prose(sign_id, language)

    merged = dict(structural)
    if prose:
        for c in _PROSE_COLS:
            merged[c] = prose.get(c)
        merged["source_url"] = prose.get("source_url")
        merged["scraped_at"] = prose.get("scraped_at")
    return merged
