"""
Panchang API endpoints.

  GET /v1/panchang  -> full panchang for a date + location
"""

from __future__ import annotations

from datetime import date as Date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query, Response, status

from services.panchang import compute_panchang, panchang_to_dict

router = APIRouter(prefix="/v1/panchang", tags=["panchang"])


# ---------------------------------------------------------------------------
# Common query validators
# ---------------------------------------------------------------------------

LatQ = Query(..., ge=-90.0, le=90.0, description="Latitude in degrees")
LonQ = Query(..., ge=-180.0, le=180.0, description="Longitude in degrees")
TzQ = Query("Asia/Kolkata", description="IANA timezone, e.g. Asia/Kolkata")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "",
    summary="Full panchang for a date + location",
)
def get_panchang(
    response: Response,
    date: Date | None = Query(None, description="YYYY-MM-DD (default: today in tz)"),
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
) -> dict:
    try:
        if date is None:
            date = datetime.now(ZoneInfo(tz)).date()
        panchang = compute_panchang(date, lat, lon, tz)
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
            detail=f"Failed to compute panchang: {e}",
        )

    response.headers["Cache-Control"] = (
        "public, max-age=3600, stale-while-revalidate=86400"
    )

    return panchang_to_dict(panchang)
