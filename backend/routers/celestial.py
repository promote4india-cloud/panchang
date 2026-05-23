"""
Celestial endpoints (endpoints.md §4).

  GET /v1/celestial/sun-moon  -> sunrise/sunset, moonrise/set, day length, moon phase
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date as Date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query, Response, status

from backend.services.cache import DEFAULT_CACHE_CONTROL, ttl_cache
from backend.services.panchang import compute_sun_moon

router = APIRouter(prefix="/v1/celestial", tags=["celestial"])

LatQ = Query(..., ge=-90.0, le=90.0, description="Latitude in degrees")
LonQ = Query(..., ge=-180.0, le=180.0, description="Longitude in degrees")
TzQ = Query("Asia/Kolkata", description="IANA timezone")


@ttl_cache(maxsize=4096, ttl_seconds=3600)
def _cached_sun_moon(date: Date, lat_q: float, lon_q: float, tz: str) -> dict:
    return asdict(compute_sun_moon(date, lat_q, lon_q, ZoneInfo(tz)))


@router.get("/sun-moon", summary="Sun & moon timings for a date + location")
def get_sun_moon(
    response: Response,
    date: Date | None = Query(None, description="YYYY-MM-DD (default: today in tz)"),
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
) -> dict:
    try:
        if date is None:
            date = datetime.now(ZoneInfo(tz)).date()
        data = _cached_sun_moon(date, round(lat, 3), round(lon, 3), tz)
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

    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    return {"date": date.isoformat(), **data}
