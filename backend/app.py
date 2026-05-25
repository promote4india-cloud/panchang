from pathlib import Path
from datetime import date
import logging
import os
import sys
import threading

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware

from backend.services.db import ensure_content_schema
from backend.services.festival_rules_seed import seed_festival_rules
from backend.services.festivals import _year_snapshot
from backend.routers.celestial import router as celestial_router
from backend.routers.festivals import router as festivals_router
from backend.routers.horoscope import router as horoscope_router
from backend.routers.locations import ensure_database, router as locations_router
from backend.routers.muhurat import router as muhurat_router
from backend.routers.panchang import router as panchang_router
from backend.routers.reference import router as reference_router
from backend.routers.scraper import router as scraper_router

ensure_database()           # GeoNames build (only on first run)
ensure_content_schema()     # additive editorial tables — safe on every boot
seed_festival_rules()       # apply curated festival rule catalog (idempotent)

log = logging.getLogger("app.prewarm")

app = FastAPI(title="Panchang API", version="0.1.0")


def _parse_prewarm_points(raw: str) -> list[tuple[float, float]]:
	points: list[tuple[float, float]] = []
	for item in raw.split(";"):
		item = item.strip()
		if not item:
			continue
		parts = item.split(":", 1)
		if len(parts) != 2:
			continue
		try:
			lat = float(parts[0].strip())
			lon = float(parts[1].strip())
		except ValueError:
			continue
		if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
			points.append((lat, lon))
	return points


def _run_snapshot_prewarm() -> None:
	if os.getenv("FESTIVAL_SNAPSHOT_PREWARM_ENABLED", "1") != "1":
		return

	default_points = "28.6139:77.2090;19.0760:72.8777;13.0827:80.2707;22.5726:88.3639"
	raw_points = os.getenv("FESTIVAL_SNAPSHOT_PREWARM_POINTS", default_points)
	points = _parse_prewarm_points(raw_points)
	if not points:
		log.warning("Snapshot prewarm skipped: no valid points configured.")
		return

	try:
		year_count = max(1, int(os.getenv("FESTIVAL_SNAPSHOT_PREWARM_YEARS", "1")))
	except ValueError:
		year_count = 1

	tz = os.getenv("FESTIVAL_SNAPSHOT_PREWARM_TZ", "Asia/Kolkata")
	ayanamsa = os.getenv("FESTIVAL_SNAPSHOT_PREWARM_AYANAMSA", "lahiri")
	start_year = date.today().year
	years = [start_year + i for i in range(year_count)]

	import time
	msg = (
		f"[prewarm] starting years={years} points={len(points)} "
		f"tz={tz} ayanamsa={ayanamsa}"
	)
	print(msg, flush=True)
	log.info(msg)
	for year in years:
		for lat, lon in points:
			t0 = time.time()
			try:
				_year_snapshot(year, round(lat, 1), round(lon, 1), tz, ayanamsa)
				dt = time.time() - t0
				done = f"[prewarm] ok year={year} lat={lat} lon={lon} in {dt:.1f}s"
				print(done, flush=True)
				log.info(done)
			except Exception as exc:  # noqa: BLE001
				err = (
					f"[prewarm] FAILED year={year} lat={lat} lon={lon}: "
					f"{type(exc).__name__}: {exc}"
				)
				print(err, flush=True)
				log.warning(err)
				import traceback
				traceback.print_exc()
	print("[prewarm] complete", flush=True)
	log.info("Snapshot prewarm complete.")


@app.on_event("startup")
def _startup_prewarm() -> None:
	threading.Thread(target=_run_snapshot_prewarm, daemon=True).start()

raw_origins = os.getenv(
	"CORS_ALLOW_ORIGINS",
	"http://localhost:8000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
)
allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(locations_router)
app.include_router(muhurat_router)
app.include_router(panchang_router)
app.include_router(celestial_router)
app.include_router(reference_router)
app.include_router(festivals_router)
app.include_router(horoscope_router)
app.include_router(scraper_router)