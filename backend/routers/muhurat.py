"""
Muhurat API endpoints.

  GET /v1/muhurat            → all 9 windows for a date+location
  GET /v1/muhurat/{id}       → single muhurat by id (for tap-through)
"""

from __future__ import annotations

from datetime import date as Date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from services.muhurat import (
    compute_muhurat,
    compute_muhurat_by_id,
)

router = APIRouter(prefix="/v1/muhurat", tags=["muhurat"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MuhuratWindowOut(BaseModel):
    id: str = Field(..., examples=["abhijit"])
    name: str = Field(..., examples=["Abhijit Muhurat"])
    start: str = Field(..., examples=["11:42"], description="Local HH:MM")
    end: str = Field(..., examples=["12:24"], description="Local HH:MM")


class MuhuratBundleOut(BaseModel):
    date: Date
    auspicious: list[MuhuratWindowOut]
    inauspicious: list[MuhuratWindowOut]


class MuhuratDetailOut(MuhuratWindowOut):
    kind: Literal["auspicious", "inauspicious"]
    description: str | None = None


# ---------------------------------------------------------------------------
# Static descriptions (i18n: move to data/i18n/{lang}.yaml later)
# ---------------------------------------------------------------------------

_DESCRIPTIONS: dict[str, str] = {
    "brahma":    "The most sacred period before sunrise, ideal for meditation, "
                 "spiritual practice, and study.",
    "abhijit":   "The victorious muhurat centered on solar noon. Auspicious for "
                 "starting important work — except travel toward the south.",
    "vijay":     "Literally 'victory'. Favorable for any action requiring courage "
                 "or strategic decisions.",
    "godhuli":   "The 'cow-dust hour' around sunset. Sacred for weddings and "
                 "religious ceremonies.",
    "amrit":     "The nectar-like time of day, governed by the active nakshatra. "
                 "All actions prosper.",
    "rahu":      "Ruled by Rahu. Avoid starting new ventures, travel, or "
                 "auspicious activities during this window.",
    "yamaganda": "Ruled by Yama. Inauspicious for new beginnings; especially "
                 "avoid travel and important meetings.",
    "gulika":    "Ruled by Gulika (son of Saturn). Whatever is started during "
                 "this period tends to repeat — avoid for one-time events.",
    "dur":       "An unfavorable muhurta of the day. Postpone significant "
                 "decisions.",
}


def _description_for(muhurat_id: str) -> str | None:
    # Handles 'dur_1', 'dur_2' → 'dur'
    base = muhurat_id.split("_", 1)[0]
    return _DESCRIPTIONS.get(base)


# ---------------------------------------------------------------------------
# Common query validators
# ---------------------------------------------------------------------------

LatQ = Query(..., ge=-90.0, le=90.0, description="Latitude in degrees")
LonQ = Query(..., ge=-180.0, le=180.0, description="Longitude in degrees")
TzQ = Query("Asia/Kolkata", description="IANA timezone, e.g. Asia/Kolkata")
LangQ = Query("en", min_length=2, max_length=5, description="ISO language code")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=MuhuratBundleOut,
    summary="All muhurat windows for a date + location",
)
def get_muhurat(
    response: Response,
    date: Date | None = Query(None, description="YYYY-MM-DD (default: today in tz)"),
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
    language: str = LangQ,
) -> MuhuratBundleOut:
    try:
        if date is None:
            date = datetime.now(ZoneInfo(tz)).date()
        bundle = compute_muhurat(date, lat, lon, tz)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid timezone: '{tz}'",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute muhurat: {e}",
        )

    # Cache: 1h fresh, 24h stale-while-revalidate (per implementation plan §7)
    response.headers["Cache-Control"] = (
        "public, max-age=3600, stale-while-revalidate=86400"
    )

    return MuhuratBundleOut(
        date=date,
        auspicious=[MuhuratWindowOut(**w.to_dict()) for w in bundle.auspicious],
        inauspicious=[MuhuratWindowOut(**w.to_dict()) for w in bundle.inauspicious],
    )


@router.get(
    "/{muhurat_id}",
    response_model=MuhuratDetailOut,
    summary="Single muhurat by id (with description)",
    responses={404: {"description": "Unknown muhurat id"}},
)
def get_muhurat_by_id(
    muhurat_id: str,
    response: Response,
    date: Date | None = Query(None, description="YYYY-MM-DD (default: today in tz)"),
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
    language: str = LangQ,
) -> MuhuratDetailOut:
    try:
        if date is None:
            date = datetime.now(ZoneInfo(tz)).date()
        window = compute_muhurat_by_id(muhurat_id, date, lat, lon, tz)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid timezone: '{tz}'",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if window is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown muhurat id: '{muhurat_id}'. "
                   f"Valid ids: brahma, abhijit, vijay, godhuli, amrit, "
                   f"rahu, yamaganda, gulika, dur (or dur_1, dur_2).",
        )

    response.headers["Cache-Control"] = (
        "public, max-age=3600, stale-while-revalidate=86400"
    )

    return MuhuratDetailOut(
        **window.to_dict(),
        kind=window.kind,
        description=_description_for(window.id),
    )