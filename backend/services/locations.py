"""
locations.py — Panchang App location service (Phase 4b)

Implements three read-only endpoints from endpoints.md §9:
  GET /v1/locations/search      — FTS5 typeahead autocomplete
  GET /v1/locations/resolve     — reverse-geocode lat/lon → tz + nearest city
  GET /v1/locations/{id}        — canonical row by GeoNames ID

Run:
    pip install fastapi "uvicorn[standard]" timezonefinder httpx pydantic
    python locations.py --build         # one-time: download GeoNames + build SQLite
    python locations.py --serve         # start API on http://localhost:8000
    python locations.py --test          # run smoke tests without HTTP

Or import into a notebook:
    from locations import build_database, search_locations, resolve_location, get_location
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import os
import sqlite3
import sys
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data" / "locations"
DB_PATH = DATA_DIR / "locations.db"

GEONAMES_BASE = "https://download.geonames.org/export/dump"

# Dataset modes:
#   "IN"             — Per-country dump for India only. ~150k populated places
#                      including villages, suburbs, neighborhoods (Bommanahalli,
#                      Whitefield, etc.). ~15 MB zipped. BEST for an India-focused app.
#   "cities500"      — Worldwide ≥500 pop. ~200k rows, ~35 MB.
#   "cities5000"     — Worldwide ≥5000 pop. ~50k rows. Spec default.
#   "cities15000"    — Worldwide ≥15000 pop. ~25k rows. Fastest, dev only.
#   "IN+cities5000"  — India full + rest-of-world ≥5000 pop. RECOMMENDED for prod.
DATASET = "IN+cities5000"

# Which countries get the "full populated places" treatment.
# Add more codes here later (e.g. "NP", "BD", "LK") as the app expands.
FULL_COUNTRIES = ["IN"]

SUPPORTED_LANGS = ("en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "sa", "or")

# Per-country dumps have an EXTRA first column (geonameid is the same, but the file
# format is identical to cities*.txt — 19 tab-separated columns).
GN_COLS = [
    "geonameid", "name", "asciiname", "alternatenames",
    "latitude", "longitude", "feature_class", "feature_code",
    "country_code", "cc2", "admin1_code", "admin2_code",
    "admin3_code", "admin4_code", "population", "elevation",
    "dem", "timezone", "modification_date",
]

# Feature classes/codes to KEEP from a per-country dump.
# Per-country dumps include mountains, rivers, parks, etc — we only want populated places.
#   feature_class = "P" → city, village, neighborhood, etc.
# Within class P, we keep everything (PPL, PPLC, PPLA, PPLA2, PPLA3, PPLA4, PPLX neighborhood, etc.)
KEEP_FEATURE_CLASS = "P"

# ---------------------------------------------------------------------------
# Step 1 — Download GeoNames files
# ---------------------------------------------------------------------------

def _download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  ✓ already have {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  ↓ downloading {url}")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r    {pct:3d}% ({downloaded // 1024:>6} KB / {total // 1024} KB)",
                          end="", flush=True)
        if total:
            print()
    print(f"  ✓ saved to {dest}")

def _resolve_dataset_files() -> list[str]:
    """Translate the DATASET config into a list of dump filenames to download."""
    files = []
    if "+" in DATASET:
        # e.g. "IN+cities5000"
        parts = DATASET.split("+")
        for p in parts:
            if len(p) == 2 and p.isupper():
                files.append(f"{p}.zip")
            else:
                files.append(f"{p}.zip")
    elif len(DATASET) == 2 and DATASET.isupper():
        files.append(f"{DATASET}.zip")
    else:
        files.append(f"{DATASET}.zip")
    return files

def download_geonames() -> dict[str, list[Path]]:
    """Download all configured dumps + admin/country metadata."""
    print(f"Downloading GeoNames data (DATASET={DATASET})...")

    city_files: list[Path] = []
    for fname in _resolve_dataset_files():
        zip_path = DATA_DIR / fname
        _download(f"{GEONAMES_BASE}/{fname}", zip_path)
        txt_name = fname.replace(".zip", ".txt")
        txt_path = DATA_DIR / txt_name
        if not txt_path.exists():
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(DATA_DIR)
            print(f"  ✓ extracted {txt_name}")
        city_files.append(txt_path)

    meta_files: dict[str, Path] = {}
    for fname in ("admin1CodesASCII.txt", "admin2Codes.txt", "countryInfo.txt"):
        dest = DATA_DIR / fname
        _download(f"{GEONAMES_BASE}/{fname}", dest)
        meta_files[fname] = dest

    return {"cities": city_files, **{k: [v] for k, v in meta_files.items()}}


# ---------------------------------------------------------------------------
# Step 2 — Build the SQLite database
# ---------------------------------------------------------------------------

DDL = """
DROP TABLE IF EXISTS geonames_cities;
CREATE TABLE geonames_cities (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    asciiname     TEXT NOT NULL,
    country       TEXT NOT NULL,
    admin1_code   TEXT,
    admin2_code   TEXT,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    tz            TEXT NOT NULL,
    population    INTEGER NOT NULL DEFAULT 0,
    feature_code  TEXT
);
CREATE INDEX idx_cities_country ON geonames_cities(country);

DROP TABLE IF EXISTS geonames_admin1;
CREATE TABLE geonames_admin1 (
    code        TEXT PRIMARY KEY,  -- e.g. "IN.36"
    name        TEXT NOT NULL,
    ascii_name  TEXT NOT NULL
);

DROP TABLE IF EXISTS geonames_admin2;
CREATE TABLE geonames_admin2 (
    code        TEXT PRIMARY KEY,  -- e.g. "IN.36.182"
    name        TEXT NOT NULL,
    ascii_name  TEXT NOT NULL
);

DROP TABLE IF EXISTS countries;
CREATE TABLE countries (
    iso2     TEXT PRIMARY KEY,
    name     TEXT NOT NULL
);

-- FTS5 virtual table for typeahead. Uses unicode61 with diacritic removal
-- so "varan" matches "Vārāṇasī" and "वाराणसी" both (with altnames loaded).
DROP TABLE IF EXISTS cities_fts;
CREATE VIRTUAL TABLE cities_fts USING fts5(
    name,           -- localized + asciiname concatenated; what we MATCH against
    content='',     -- contentless: we manage rows manually
    tokenize="unicode61 remove_diacritics 2"
);

-- R*Tree for /resolve's nearest-city query
DROP TABLE IF EXISTS cities_rtree;
CREATE VIRTUAL TABLE cities_rtree USING rtree(
    id,             -- matches geonames_cities.id
    min_lat, max_lat,
    min_lon, max_lon
);
"""


def build_database(paths: dict[str, list[Path]]) -> None:
    print(f"\nBuilding SQLite database at {DB_PATH}...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)

    # --- countries ----------------------------------------------------------
    print("  · loading countries...")
    with paths["countryInfo.txt"][0].open(encoding="utf-8") as f:
        rows = []
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            rows.append((parts[0], parts[4]))
        conn.executemany("INSERT INTO countries VALUES (?, ?)", rows)
    print(f"    ✓ {len(rows)} countries")

    # --- admin1 -------------------------------------------------------------
    print("  · loading admin1 (states/provinces)...")
    with paths["admin1CodesASCII.txt"][0].open(encoding="utf-8") as f:
        rows = [tuple(line.rstrip("\n").split("\t")[:3]) for line in f if line.strip()]
        conn.executemany("INSERT INTO geonames_admin1 VALUES (?, ?, ?)", rows)
    print(f"    ✓ {len(rows)} admin1 regions")

    # --- admin2 -------------------------------------------------------------
    print("  · loading admin2 (districts)...")
    with paths["admin2Codes.txt"][0].open(encoding="utf-8") as f:
        rows = [tuple(line.rstrip("\n").split("\t")[:3]) for line in f if line.strip()]
        conn.executemany("INSERT INTO geonames_admin2 VALUES (?, ?, ?)", rows)
    print(f"    ✓ {len(rows)} admin2 regions")

    # --- cities -------------------------------------------------------------
    # We dedupe by geonameid because a row might appear in BOTH IN.txt and cities5000.txt
    # (most major Indian cities will). The per-country dump wins because it has richer
    # admin2 codes.
    print(f"  · loading {len(paths['cities'])} city file(s)...")
    by_id: dict[int, tuple] = {}
    fts_by_id: dict[int, str] = {}

    for cities_file in paths["cities"]:
        is_country_dump = len(cities_file.stem) == 2 and cities_file.stem.isupper()
        print(f"    · parsing {cities_file.name} (country-dump={is_country_dump})...")
        kept = 0
        skipped = 0
        with cities_file.open(encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
            for row in reader:
                if len(row) < len(GN_COLS):
                    continue
                d = dict(zip(GN_COLS, row))

                # Per-country dumps include EVERYTHING (mountains, rivers...).
                # Keep only populated places.
                if is_country_dump and d["feature_class"] != KEEP_FEATURE_CLASS:
                    skipped += 1
                    continue

                gid = int(d["geonameid"])
                # Per-country dump overrides cities*.txt for the same id
                if gid in by_id and not is_country_dump:
                    continue

                try:
                    lat = float(d["latitude"])
                    lon = float(d["longitude"])
                except ValueError:
                    continue
                pop = int(d["population"] or 0)

                by_id[gid] = (
                    gid, d["name"], d["asciiname"], d["country_code"],
                    f"{d['country_code']}.{d['admin1_code']}" if d["admin1_code"] else None,
                    f"{d['country_code']}.{d['admin1_code']}.{d['admin2_code']}"
                        if d["admin1_code"] and d["admin2_code"] else None,
                    lat, lon, d["timezone"] or "UTC", pop, d["feature_code"],
                )
                fts_by_id[gid] = " ".join(filter(None, [
                    d["name"], d["asciiname"], d["alternatenames"]
                ]))
                kept += 1
        print(f"      kept={kept:,}  skipped(non-populated)={skipped:,}")

    cities_rows = list(by_id.values())
    fts_rows = [(gid, txt) for gid, txt in fts_by_id.items()]
    rtree_rows = [(r[0], r[6], r[6], r[7], r[7]) for r in cities_rows]

    conn.executemany(
        "INSERT INTO geonames_cities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        cities_rows,
    )
    conn.executemany("INSERT INTO cities_fts(rowid, name) VALUES (?, ?)", fts_rows)
    conn.executemany("INSERT INTO cities_rtree VALUES (?, ?, ?, ?, ?)", rtree_rows)

    conn.commit()
    conn.close()
    print(f"\n✓ {len(cities_rows):,} unique populated places indexed")
    print(f"✓ Database ready at {DB_PATH} ({DB_PATH.stat().st_size / 1024 / 1024:.1f} MB)")

# ---------------------------------------------------------------------------
# Step 3 — Core query functions (the actual endpoint logic)
# ---------------------------------------------------------------------------

@dataclass
class LocationRow:
    """Mirrors the shape from endpoints.md §9."""
    id: int
    name: str
    name_localized: str
    admin2: Optional[str]
    admin1: Optional[str]
    admin1_localized: Optional[str]
    country: str
    country_localized: str
    lat: float
    lon: float
    tz: str
    population: int
    feature_code: Optional[str]
    display_label: str


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise RuntimeError(f"Database missing at {DB_PATH}. Run: python locations.py --build")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _build_label(name: str, admin1: Optional[str], country: str) -> str:
    """Shortest unique label per spec §9."""
    parts = [name]
    if admin1:
        parts.append(admin1)
    parts.append(country)
    return ", ".join(parts)


def _hydrate_row(conn: sqlite3.Connection, row: sqlite3.Row, language: str) -> LocationRow:
    """Join a cities row with admin1 + country names. Localization stub for now."""
    admin1_name = None
    if row["admin1_code"]:
        a1 = conn.execute(
            "SELECT name FROM geonames_admin1 WHERE code = ?",
            (row["admin1_code"],),
        ).fetchone()
        if a1:
            admin1_name = a1["name"]

    admin2_name = None
    if row["admin2_code"]:
        a2 = conn.execute(
            "SELECT name FROM geonames_admin2 WHERE code = ?",
            (row["admin2_code"],),
        ).fetchone()
        if a2:
            admin2_name = a2["name"]

    country = conn.execute(
        "SELECT name FROM countries WHERE iso2 = ?", (row["country"],)
    ).fetchone()
    country_name = country["name"] if country else row["country"]

    # TODO: localize via alternateNamesV2 once we import it. For now, returns English.
    name_localized = row["name"]
    admin1_localized = admin1_name
    country_localized = country_name

    return LocationRow(
        id=row["id"],
        name=row["name"],
        name_localized=name_localized,
        admin2=admin2_name,
        admin1=admin1_name,
        admin1_localized=admin1_localized,
        country=row["country"],
        country_localized=country_localized,
        lat=row["lat"],
        lon=row["lon"],
        tz=row["tz"],
        population=row["population"],
        feature_code=row["feature_code"],
        display_label=_build_label(name_localized, admin1_localized, country_localized),
    )


# Feature-code ranking per spec §9 rule 3
_FEATURE_RANK = {"PPLC": 0, "PPLA": 1, "PPLA2": 2, "PPLA3": 3, "PPLA4": 4, "PPL": 5}


def search_locations(
    q: str,
    country: Optional[str] = None,
    language: str = "en",
    limit: int = 10,
) -> list[dict]:
    """Implements GET /v1/locations/search per endpoints.md §9."""
    if not q or len(q) < 1 or len(q) > 64:
        raise ValueError("q must be 1–64 chars")
    limit = max(1, min(25, limit))

    # Escape FTS5 special chars and add prefix wildcard
    safe_q = q.replace('"', '""')
    fts_query = f'"{safe_q}"*'  # quoted phrase + prefix

    conn = _connect()
    try:
        sql = """
            SELECT c.*,
                   CASE WHEN lower(c.name) = lower(:q) OR lower(c.asciiname) = lower(:q)
                        THEN 0 ELSE 1 END AS exact_rank,
                   CASE WHEN c.country = :country THEN 0 ELSE 1 END AS country_rank
            FROM cities_fts
            JOIN geonames_cities c ON c.id = cities_fts.rowid
            WHERE cities_fts MATCH :fts
            ORDER BY
                country_rank,
                exact_rank,
                CASE c.feature_code
                    WHEN 'PPLC'  THEN 0
                    WHEN 'PPLA'  THEN 1
                    WHEN 'PPLA2' THEN 2
                    WHEN 'PPLA3' THEN 3
                    WHEN 'PPLA4' THEN 4
                    ELSE 5
                END,
                c.population DESC,
                c.id ASC
            LIMIT :limit
        """
        rows = conn.execute(sql, {
            "q": q, "country": country or "", "fts": fts_query, "limit": limit
        }).fetchall()

        results = [_hydrate_row(conn, r, language) for r in rows]

        # Collision detection: if two results share name+admin1, switch to longer label
        seen: dict[str, list[int]] = {}
        for i, r in enumerate(results):
            seen.setdefault(r.display_label, []).append(i)
        for label, idxs in seen.items():
            if len(idxs) > 1:
                for i in idxs:
                    r = results[i]
                    if r.admin2:
                        new_label = f"{r.name_localized}, {r.admin2} dist., "
                        new_label += f"{r.admin1_localized + ', ' if r.admin1_localized else ''}"
                        new_label += r.country_localized
                        results[i] = LocationRow(**{**asdict(r), "display_label": new_label})

        return [asdict(r) for r in results]
    finally:
        conn.close()


def get_location(geonameid: int, language: str = "en") -> Optional[dict]:
    """Implements GET /v1/locations/{id}."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM geonames_cities WHERE id = ?", (geonameid,)
        ).fetchone()
        if not row:
            return None
        return asdict(_hydrate_row(conn, row, language))
    finally:
        conn.close()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# Lazy-loaded timezonefinder singleton
_tz_finder = None
def _get_tz_finder():
    global _tz_finder
    if _tz_finder is None:
        from timezonefinder import TimezoneFinder
        _tz_finder = TimezoneFinder(in_memory=True)
    return _tz_finder


def resolve_location(lat: float, lon: float, language: str = "en") -> dict:
    """Implements GET /v1/locations/resolve."""
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError("lat/lon out of range")

    tz = _get_tz_finder().timezone_at(lat=lat, lng=lon) or "UTC"

    # Bounding-box search via R*Tree, expanding until we find candidates.
    # Start at ~50 km box (0.5°), grow if empty.
    conn = _connect()
    try:
        nearest = None
        nearest_dist = float("inf")
        for delta in (0.5, 2.0, 10.0):  # ~50, ~220, ~1100 km
            sql = """
                SELECT c.* FROM cities_rtree r
                JOIN geonames_cities c ON c.id = r.id
                WHERE r.min_lat >= ? AND r.max_lat <= ?
                  AND r.min_lon >= ? AND r.max_lon <= ?
            """
            rows = conn.execute(sql, (
                lat - delta, lat + delta, lon - delta, lon + delta
            )).fetchall()
            for r in rows:
                d = _haversine_km(lat, lon, r["lat"], r["lon"])
                if d < nearest_dist:
                    nearest_dist = d
                    nearest = r
            if nearest:
                break

        out = {"tz": tz, "nearest_city": None}
        if nearest:
            hydrated = _hydrate_row(conn, nearest, language)
            out["nearest_city"] = {
                "id": hydrated.id,
                "name": hydrated.name_localized,
                "admin1": hydrated.admin1_localized,
                "country": hydrated.country,
                "lat": hydrated.lat,
                "lon": hydrated.lon,
                "display_label": hydrated.display_label,
                "distance_km": round(nearest_dist, 2),
            }
        return out
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Step 4 — FastAPI router
# ---------------------------------------------------------------------------

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1/locations", tags=["locations"])


def ensure_database() -> None:
    if DB_PATH.exists():
        return
    paths = download_geonames()
    build_database(paths)


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


# ---------------------------------------------------------------------------
# Step 5 — Smoke tests (run without HTTP)
# ---------------------------------------------------------------------------

def run_tests():
    print("\n=== Smoke tests ===\n")

    print("1. search('varan') — expect Varanasi:")
    for r in search_locations("varan", country="IN", limit=5):
        print(f"   {r['display_label']:60s} pop={r['population']:>10,}")

    print("\n2. search('aurang') — both Aurangabads disambiguated:")
    for r in search_locations("aurang", country="IN", limit=5):
        print(f"   {r['display_label']:60s} admin2={r['admin2']}")

    print("\n3. search('bommanahalli') — Bangalore suburb (needs IN dump!):")
    for r in search_locations("bommanahalli", country="IN", limit=5):
        print(f"   {r['display_label']:60s} pop={r['population']:>10,}  feat={r['feature_code']}")

    print("\n4. search('whitefield') — another Bangalore neighborhood:")
    for r in search_locations("whitefield", country="IN", limit=5):
        print(f"   {r['display_label']:60s} feat={r['feature_code']}")

    print("\n5. search('koramangala') — Bangalore neighborhood:")
    for r in search_locations("koramangala", country="IN", limit=5):
        print(f"   {r['display_label']:60s} feat={r['feature_code']}")

    print("\n6. resolve(12.9082, 77.6476) — Bommanahalli coords, expect Asia/Kolkata:")
    res = resolve_location(12.9082, 77.6476)
    print(f"   tz={res['tz']}")
    if res["nearest_city"]:
        nc = res["nearest_city"]
        print(f"   nearest: {nc['display_label']} ({nc['distance_km']} km)")

    print("\n✓ All smoke tests done.\n")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Download GeoNames + build SQLite")
    parser.add_argument("--serve", action="store_true", help="Run FastAPI on :8000")
    parser.add_argument("--test", action="store_true", help="Run smoke tests")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.build:
        paths = download_geonames()
        build_database(paths)

    if args.serve or args.test:
        ensure_database()

    if args.test:
        run_tests()

    if args.serve:
        backend_root = Path(__file__).resolve().parents[1]
        if str(backend_root) not in sys.path:
            sys.path.insert(0, str(backend_root))
        import uvicorn
        uvicorn.run("app:app", host="0.0.0.0", port=args.port, reload=False)

    if not any([args.build, args.serve, args.test]):
        parser.print_help()