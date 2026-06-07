"""
Panchang API endpoints (endpoints.md §1 + §2).

  GET /v1/panchang                  -> full panchang for a date + location
  GET /v1/panchang/today            -> dashboard alias (today in tz)
  GET /v1/panchang/tithi-nakshatra  -> tithi + nakshatra detail only
"""

from __future__ import annotations

from datetime import date as Date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from backend.auth import require_user
from backend.services.cache import DEFAULT_CACHE_CONTROL, ttl_cache
from backend.services.panchang import compute_panchang, panchang_to_dict

router = APIRouter(
    prefix="/v1/panchang",
    tags=["panchang"],
    dependencies=[Depends(require_user)],
)


# ---------------------------------------------------------------------------
# Common query validators
# ---------------------------------------------------------------------------

LatQ = Query(..., ge=-90.0, le=90.0, description="Latitude in degrees")
LonQ = Query(..., ge=-180.0, le=180.0, description="Longitude in degrees")
TzQ = Query("Asia/Kolkata", description="IANA timezone, e.g. Asia/Kolkata")


# ---------------------------------------------------------------------------
# Memoized compute (per-worker TTL cache; deterministic in inputs)
# ---------------------------------------------------------------------------

@ttl_cache(maxsize=4096, ttl_seconds=3600)
def _cached_panchang_dict(date: Date, lat_q: float, lon_q: float, tz: str) -> dict:
    return panchang_to_dict(compute_panchang(date, lat_q, lon_q, tz))


def _q(x: float) -> float:
    """Quantize lat/lon to ~100 m grid (3 decimals) so cache hits coalesce."""
    return round(x, 3)


def _resolve_panchang(date: Date | None, lat: float, lon: float, tz: str) -> dict:
    try:
        if date is None:
            date = datetime.now(ZoneInfo(tz)).date()
        return _cached_panchang_dict(date, _q(lat), _q(lon), tz)
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", summary="Full panchang for a date + location")
def get_panchang(
    response: Response,
    date: Date | None = Query(None, description="YYYY-MM-DD (default: today in tz)"),
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
) -> dict:
    data = _resolve_panchang(date, lat, lon, tz)
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    return data


@router.get(
    "/today",
    summary="Panchang for today in the requested timezone (dashboard alias)",
)
def get_panchang_today(
    response: Response,
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
) -> dict:
    data = _resolve_panchang(None, lat, lon, tz)
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    return data


@router.get(
    "/tithi-nakshatra",
    summary="Just the tithi + nakshatra block (for detail screens)",
)
def get_tithi_nakshatra(
    response: Response,
    date: Date | None = Query(None, description="YYYY-MM-DD (default: today in tz)"),
    lat: float = LatQ,
    lon: float = LonQ,
    tz: str = TzQ,
) -> dict:
    data = _resolve_panchang(date, lat, lon, tz)
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    return {
        "date": data["date"],
        "weekday": data["weekday"],
        "tithi": data["tithi"],
        "nakshatra": data["nakshatra"],
    }
