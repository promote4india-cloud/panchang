"""
Static reference catalogs (endpoints.md §2 / §6 / §10).

  GET /v1/reference/tithis        -> 30 tithis (name, paksha, lord)
  GET /v1/reference/nakshatras    -> 27 nakshatras (symbol, deity, element)
  GET /v1/reference/zodiac-signs  -> 12 rashis (name, lord, tropical date range)
  GET /v1/reference/languages     -> supported UI / i18n languages

Catalogs are pure constants, served with a long Cache-Control window.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, Response

from backend.services.cache import DEFAULT_CACHE_CONTROL
from backend.services.panchang import (
    NAKSHATRA_DEITIES,
    NAKSHATRA_ELEMENTS,
    NAKSHATRA_NAMES,
    NAKSHATRA_SYMBOLS,
    TITHI_LORDS,
    TITHI_NAMES,
)
from backend.services.zodiac import (
    SIGN_IDS,
    get_zodiac_sign,
    zodiac_index,
)

router = APIRouter(prefix="/v1/reference", tags=["reference"])

# Long-lived static data — week-long cache window.
_STATIC_CACHE_CONTROL = "public, max-age=604800, stale-while-revalidate=2592000"


# ---------------------------------------------------------------------------
# Tithis (30)
# ---------------------------------------------------------------------------

def _build_tithis() -> list[dict]:
    items: list[dict] = []
    for i, name in enumerate(TITHI_NAMES):
        paksha = "Shukla" if i < 15 else "Krishna"
        items.append(
            {
                "index": i + 1,
                "name": name,
                "paksha": paksha,
                "lord": TITHI_LORDS[i],
            }
        )
    return items


_TITHIS = _build_tithis()


@router.get("/tithis", summary="Static catalog of 30 tithis")
def get_tithis(response: Response) -> dict:
    response.headers["Cache-Control"] = _STATIC_CACHE_CONTROL
    return {"items": _TITHIS}


# ---------------------------------------------------------------------------
# Nakshatras (27)
# ---------------------------------------------------------------------------

def _build_nakshatras() -> list[dict]:
    items: list[dict] = []
    for i, name in enumerate(NAKSHATRA_NAMES):
        items.append(
            {
                "index": i + 1,
                "name": name,
                "symbol": NAKSHATRA_SYMBOLS[i],
                "deity": NAKSHATRA_DEITIES[i],
                "element": NAKSHATRA_ELEMENTS[i],
                "padas": 4,
            }
        )
    return items


_NAKSHATRAS = _build_nakshatras()


@router.get("/nakshatras", summary="Static catalog of 27 nakshatras")
def get_nakshatras(response: Response) -> dict:
    response.headers["Cache-Control"] = _STATIC_CACHE_CONTROL
    return {"items": _NAKSHATRAS}


# ---------------------------------------------------------------------------
# Zodiac signs (12).
#   GET /zodiac-signs       -> static catalog (structural fields only)
#   GET /zodiac-signs/{id}  -> structural + prose; prose is lazy-scraped
#                              from astrosage on first read per (id, lang)
# Structural source of truth lives in services/zodiac.py; the prose-only
# DB table (`zodiac_signs`) is filled on demand and merged in.
# ---------------------------------------------------------------------------

_ZODIAC = zodiac_index()
_SIGN_PATTERN = "^(" + "|".join(SIGN_IDS) + ")$"


@router.get("/zodiac-signs", summary="Static catalog of 12 zodiac signs")
def get_zodiac_signs(response: Response) -> dict:
    response.headers["Cache-Control"] = _STATIC_CACHE_CONTROL
    return {"items": _ZODIAC}


@router.get(
    "/zodiac-signs/{sign_id}",
    summary="Single zodiac sign — structural fields + lazy-scraped prose",
)
async def get_zodiac_sign_detail(
    response: Response,
    sign_id: str = Path(..., pattern=_SIGN_PATTERN, description="Zodiac sign id (lowercase English)."),
    language: str = Query("en", min_length=2, max_length=5),
    force: bool = Query(
        False,
        description=(
            "Bypass the DB cache and re-scrape prose fields from astrosage. "
            "Respects the 1 req/s polite throttle."
        ),
    ),
) -> dict:
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    merged = await get_zodiac_sign(sign_id=sign_id, language=language, force=force)
    if merged is None:
        raise HTTPException(404, f"Unknown zodiac sign: {sign_id!r}")
    return merged


# ---------------------------------------------------------------------------
# Languages (12 supported, per implementation.md §8)
# ---------------------------------------------------------------------------

_LANGUAGES = [
    {"code": "en", "name": "English",   "native_name": "English"},
    {"code": "hi", "name": "Hindi",     "native_name": "हिन्दी"},
    {"code": "bn", "name": "Bengali",   "native_name": "বাংলা"},
    {"code": "ta", "name": "Tamil",     "native_name": "தமிழ்"},
    {"code": "te", "name": "Telugu",    "native_name": "తెలుగు"},
    {"code": "mr", "name": "Marathi",   "native_name": "मराठी"},
    {"code": "gu", "name": "Gujarati",  "native_name": "ગુજરાતી"},
    {"code": "kn", "name": "Kannada",   "native_name": "ಕನ್ನಡ"},
    {"code": "ml", "name": "Malayalam", "native_name": "മലയാളം"},
    {"code": "pa", "name": "Punjabi",   "native_name": "ਪੰਜਾਬੀ"},
    {"code": "sa", "name": "Sanskrit",  "native_name": "संस्कृतम्"},
    {"code": "or", "name": "Odia",      "native_name": "ଓଡ଼ିଆ"},
]


@router.get("/languages", summary="Supported UI / i18n languages")
def get_languages(response: Response) -> dict:
    response.headers["Cache-Control"] = _STATIC_CACHE_CONTROL
    return {"items": _LANGUAGES, "default": "en"}
