from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.auth import require_user
from backend.services.locations import (
    ensure_database,
    get_location,
    resolve_location,
    search_locations,
)

router = APIRouter(
    prefix="/v1/locations",
    tags=["locations"],
    dependencies=[Depends(require_user)],
)


@router.get("/search")
def api_search(
    q: str = Query(..., min_length=1, max_length=64),
    country: Optional[str] = Query(None, min_length=2, max_length=2),
    language: str = Query("en"),
    limit: int = Query(10, ge=1, le=25),
    include_small: bool = Query(False),  # accepted but currently no-op
):
    try:
        results = search_locations(q, country, language, limit)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return JSONResponse(
        {"results": results},
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"},
    )


@router.get("/resolve")
def api_resolve(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    language: str = Query("en"),
):
    return JSONResponse(
        resolve_location(lat, lon, language),
        headers={"Cache-Control": "public, max-age=604800"},
    )


@router.get("/{geonameid}")
def api_get(geonameid: int, language: str = Query("en")):
    row = get_location(geonameid, language)
    if not row:
        raise HTTPException(404, "Location not found")
    return JSONResponse(
        row,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )
