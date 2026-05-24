"""
Muhurat API endpoints.

    GET /v1/muhurat            → all 30 classical muhurtas for a date+location
  GET /v1/muhurat/{id}       → single muhurat by id (for tap-through)
"""

from __future__ import annotations

from datetime import date as Date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from backend.services.muhurat import (
    compute_muhurat,
    compute_muhurat_by_id,
)

router = APIRouter(prefix="/v1/muhurat", tags=["muhurat"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MuhuratWindowOut(BaseModel):
    id: str = Field(..., examples=["rudra"])
    sequence: int = Field(..., examples=[1], ge=1, le=30)
    name: str = Field(..., examples=["Rudra"])
    sanskrit_name: str = Field(..., examples=["Rudra"])
    sanskrit_devanagari: str = Field(..., examples=["रुद्र"])
    category: str = Field(..., examples=["inauspicious"])
    period: str = Field(..., examples=["day"])
    start: str = Field(..., examples=["06:00"], description="Local HH:MM")
    end: str = Field(..., examples=["06:48"], description="Local HH:MM")


class MuhuratBundleOut(BaseModel):
    date: Date
    muhurtas: list[MuhuratWindowOut]


class MuhuratDetailOut(MuhuratWindowOut):
    description: str | None = None


# ---------------------------------------------------------------------------
# Static descriptions (i18n: move to data/i18n/{lang}.yaml later)
# ---------------------------------------------------------------------------

_DESCRIPTIONS: dict[str, str] = {
    "rudra": "Classical muhurta associated with intensity and disruption; avoid major beginnings.",
    "ahi": "Classical muhurta associated with instability; generally avoided for auspicious starts.",
    "yama": "Classical muhurta associated with restraint and endings; avoid fresh undertakings.",
    "brahma": "Highly regarded pre-dawn classical muhurta for spiritual practice and study.",
}


def _description_for(muhurat_id: str) -> str | None:
    return _DESCRIPTIONS.get(muhurat_id)


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
    summary="All 30 classical muhurtas for a date + location",
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
        muhurtas=[MuhuratWindowOut(**w.to_dict()) for w in bundle.muhurtas],
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
                   "Use GET /v1/muhurat to list all supported ids.",
        )

    response.headers["Cache-Control"] = (
        "public, max-age=3600, stale-while-revalidate=86400"
    )

    return MuhuratDetailOut(
        **window.to_dict(),
        description=_description_for(window.id),
    )