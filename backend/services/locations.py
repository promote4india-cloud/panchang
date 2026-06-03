"""
locations.py — Panchang App location service

Implements three read-only endpoints from endpoints.md §9:
  GET /v1/locations/search      — pg_trgm prefix typeahead autocomplete
  GET /v1/locations/resolve     — reverse-geocode lat/lon → tz + nearest city
  GET /v1/locations/{id}        — canonical row by GeoNames ID

GeoNames data is downloaded once and loaded into the shared PostgreSQL
database. On subsequent startups the data is already present and the build
step is skipped automatically.

Run:
    python locations.py --build         # one-time: download GeoNames + build PG
    python locations.py --test          # run smoke tests without HTTP

Or import:
    from locations import build_database, search_locations, resolve_location, get_location
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import httpx
import psycopg
from psycopg.rows import dict_row

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Local data directory only used for GeoNames file downloads.
DATA_DIR = Path(__file__).parent / "data"

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
FULL_COUNTRIES = ["IN"]

SUPPORTED_LANGS = ("en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "sa", "or")

GN_COLS = [
    "geonameid", "name", "asciiname", "alternatenames",
    "latitude", "longitude", "feature_class", "feature_code",
    "country_code", "cc2", "admin1_code", "admin2_code",
    "admin3_code", "admin4_code", "population", "elevation",
    "dem", "timezone", "modification_date",
]

KEEP_FEATURE_CLASS = "P"


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def _connect() -> psycopg.Connection:
    from backend.config import DATABASE_URL
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Add it to your .env file or set it as an environment variable."
        )
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


# ---------------------------------------------------------------------------
# Step 1 — Download GeoNames files
# ---------------------------------------------------------------------------

def _download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  [ok] already have {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  [dl] downloading {url}")
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
        print(f"  [ok] saved to {dest}")


def _resolve_dataset_files() -> list[str]:
    """Translate the DATASET config into a list of dump filenames to download."""
    files = []
    if "+" in DATASET:
        parts = DATASET.split("+")
        for p in parts:
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
            print(f"  [ok] extracted {txt_name}")
        city_files.append(txt_path)

    meta_files: dict[str, Path] = {}
    for fname in ("admin1CodesASCII.txt", "admin2Codes.txt", "countryInfo.txt"):
        dest = DATA_DIR / fname
        _download(f"{GEONAMES_BASE}/{fname}", dest)
        meta_files[fname] = dest

    return {"cities": city_files, **{k: [v] for k, v in meta_files.items()}}


# ---------------------------------------------------------------------------
# Step 2 — Build the PostgreSQL database
# ---------------------------------------------------------------------------

_GEONAMES_TABLES = (
    "geonames_cities",
    "geonames_admin1",
    "geonames_admin2",
    "countries",
)

# Indexes specific to the GeoNames tables (dropped before rebuild).
_GEONAMES_INDEXES = (
    "idx_cities_country",
    "idx_cities_lat_lon",
    "idx_cities_name_trgm",
    "idx_cities_ascii_trgm",
)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _reset_geonames_tables(conn: psycopg.Connection) -> None:
    """Drop GeoNames-owned tables so a rebuild starts clean."""
    for idx in _GEONAMES_INDEXES:
        conn.execute(f"DROP INDEX IF EXISTS {idx}")
    for t in _GEONAMES_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {t} CASCADE")


def build_database(paths: dict[str, list[Path]]) -> None:
    print("\nBuilding GeoNames tables in PostgreSQL...")
    conn = _connect()
    try:
        with conn.transaction():
            _reset_geonames_tables(conn)

        # Re-apply schema to recreate dropped tables + indexes
        ddl = SCHEMA_PATH.read_text(encoding="utf-8")
        statements = [s.strip() for s in ddl.split(";") if s.strip()]
        with conn.transaction():
            for stmt in statements:
                conn.execute(stmt)

        # --- countries ---
        print("  · loading countries...")
        rows_c = []
        with paths["countryInfo.txt"][0].open(encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                rows_c.append((parts[0], parts[4]))
        with conn.transaction():
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO countries VALUES (%s, %s) ON CONFLICT DO NOTHING", rows_c)
        print(f"    [ok] {len(rows_c)} countries")

        # --- admin1 ---
        print("  · loading admin1 (states/provinces)...")
        with paths["admin1CodesASCII.txt"][0].open(encoding="utf-8") as f:
            rows_a1 = [tuple(line.rstrip("\n").split("\t")[:3]) for line in f if line.strip()]
        with conn.transaction():
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO geonames_admin1 VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", rows_a1
                )
        print(f"    [ok] {len(rows_a1)} admin1 regions")

        # --- admin2 ---
        print("  · loading admin2 (districts)...")
        with paths["admin2Codes.txt"][0].open(encoding="utf-8") as f:
            rows_a2 = [tuple(line.rstrip("\n").split("\t")[:3]) for line in f if line.strip()]
        with conn.transaction():
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO geonames_admin2 VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", rows_a2
                )
        print(f"    [ok] {len(rows_a2)} admin2 regions")

        # --- cities ---
        print(f"  · loading {len(paths['cities'])} city file(s)...")
        by_id: dict[int, tuple] = {}

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
                    if is_country_dump and d["feature_class"] != KEEP_FEATURE_CLASS:
                        skipped += 1
                        continue
                    gid = int(d["geonameid"])
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
                    kept += 1
            print(f"      kept={kept:,}  skipped(non-populated)={skipped:,}")

        cities_rows = list(by_id.values())
        BATCH = 5000
        total = len(cities_rows)
        print(f"  · inserting {total:,} cities in batches of {BATCH}...")
        with conn.transaction():
            with conn.cursor() as cur:
                for i in range(0, total, BATCH):
                    batch = cities_rows[i: i + BATCH]
                    cur.executemany(
                        """
                        INSERT INTO geonames_cities
                            (id, name, asciiname, country, admin1_code, admin2_code,
                             lat, lon, tz, population, feature_code)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        batch,
                    )
                    if (i // BATCH) % 10 == 0:
                        print(f"    ... {min(i + BATCH, total):,}/{total:,}", end="\r", flush=True)
        print()

        conn.commit()
        print(f"\n[ok] {total:,} unique populated places loaded into PostgreSQL")

    finally:
        conn.close()


def ensure_database() -> None:
    """
    Called at startup. Builds the GeoNames database if the cities table is
    empty. On first deploy this triggers a ~3-minute download+import.
    Subsequent restarts skip this entirely.
    """
    try:
        conn = _connect()
        try:
            row = conn.execute("SELECT COUNT(*) AS n FROM geonames_cities").fetchone()
            count = row["n"] if row else 0
        finally:
            conn.close()
    except Exception:
        count = 0

    if count > 0:
        print(f"[locations] GeoNames DB ready ({count:,} cities — skipping rebuild)")
        return

    print("[locations] GeoNames DB empty — starting first-time build...")
    paths = download_geonames()
    build_database(paths)


# ---------------------------------------------------------------------------
# Step 3 — Core query functions
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


def _build_label(name: str, admin1: Optional[str], country: str) -> str:
    """Shortest unique label per spec §9."""
    parts = [name]
    if admin1:
        parts.append(admin1)
    parts.append(country)
    return ", ".join(parts)


def _hydrate_row(conn: psycopg.Connection, row: dict, language: str) -> LocationRow:
    """Join a cities row with admin1 + country names."""
    admin1_name = None
    if row.get("admin1_code"):
        a1 = conn.execute(
            "SELECT name FROM geonames_admin1 WHERE code = %s",
            (row["admin1_code"],),
        ).fetchone()
        if a1:
            admin1_name = a1["name"]

    admin2_name = None
    if row.get("admin2_code"):
        a2 = conn.execute(
            "SELECT name FROM geonames_admin2 WHERE code = %s",
            (row["admin2_code"],),
        ).fetchone()
        if a2:
            admin2_name = a2["name"]

    country = conn.execute(
        "SELECT name FROM countries WHERE iso2 = %s", (row["country"],)
    ).fetchone()
    country_name = country["name"] if country else row["country"]

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
        feature_code=row.get("feature_code"),
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
    """Implements GET /v1/locations/search per endpoints.md §9.

    Uses pg_trgm ILIKE prefix matching on name/asciiname columns — equivalent
    to the old SQLite FTS5 `MATCH "query"*` prefix search.
    """
    if not q or len(q) < 1 or len(q) > 64:
        raise ValueError("q must be 1–64 chars")
    limit = max(1, min(25, limit))

    q_prefix = q + "%"   # prefix match for typeahead

    conn = _connect()
    try:
        sql = """
            SELECT *,
                   CASE WHEN lower(name) = lower(%(q)s) OR lower(asciiname) = lower(%(q)s)
                        THEN 0 ELSE 1 END AS exact_rank,
                   CASE WHEN country = %(country)s THEN 0 ELSE 1 END AS country_rank
            FROM geonames_cities
            WHERE name      ILIKE %(q_prefix)s
               OR asciiname ILIKE %(q_prefix)s
            ORDER BY
                country_rank,
                exact_rank,
                CASE feature_code
                    WHEN 'PPLC'  THEN 0
                    WHEN 'PPLA'  THEN 1
                    WHEN 'PPLA2' THEN 2
                    WHEN 'PPLA3' THEN 3
                    WHEN 'PPLA4' THEN 4
                    ELSE 5
                END,
                population DESC,
                id ASC
            LIMIT %(limit)s
        """
        rows = conn.execute(sql, {
            "q": q, "q_prefix": q_prefix, "country": country or "", "limit": limit
        }).fetchall()

        results = [_hydrate_row(conn, r, language) for r in rows]

        # Collision detection: if two results share display_label, use longer label
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
            "SELECT * FROM geonames_cities WHERE id = %s", (geonameid,)
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
    """Implements GET /v1/locations/resolve.

    Uses a simple bounding-box WHERE clause on lat/lon — equivalent to the
    old SQLite R*Tree virtual table. The idx_cities_lat_lon btree index makes
    this fast enough for the typical ±2° search boxes used here.
    """
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError("lat/lon out of range")

    tz = _get_tz_finder().timezone_at(lat=lat, lng=lon) or "UTC"

    conn = _connect()
    try:
        nearest = None
        nearest_dist = float("inf")
        # Expand bounding box until we find candidates.
        for delta in (0.5, 2.0, 10.0):  # ~50, ~220, ~1100 km
            sql = """
                SELECT * FROM geonames_cities
                 WHERE lat BETWEEN %s AND %s
                   AND lon BETWEEN %s AND %s
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

        out: dict = {"tz": tz, "nearest_city": None}
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
# CLI entry point (for --build / --test)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Download GeoNames and load into Postgres")
    parser.add_argument("--test", action="store_true", help="Run smoke tests")
    args = parser.parse_args()

    if args.build:
        paths = download_geonames()
        build_database(paths)

    if args.test:
        r = search_locations("Delhi", country="IN")
        print(f"search 'Delhi': {len(r)} results, first={r[0]['name'] if r else 'none'}")
        r2 = resolve_location(28.6139, 77.2090)
        print(f"resolve Delhi: tz={r2['tz']}, nearest={r2['nearest_city']}")
        print("✓ smoke tests passed")