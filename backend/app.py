from pathlib import Path
from datetime import date
import logging
import sys
import threading

# Make the repository root importable when running `uvicorn app:app` from
# inside the backend directory.
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env FIRST — before any backend.* imports read os.getenv() via config.py.
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Print LLM config at startup so running process shows which model/key it will use
try:
	from backend.config import LLM_MODEL, GEMINI_API_KEY
	masked = None if not GEMINI_API_KEY else GEMINI_API_KEY[:8] + "..."
	print(f"[startup] LLM config: LLM_MODEL={LLM_MODEL} GEMINI_API_KEY_set={bool(GEMINI_API_KEY)} GEMINI_API_KEY={masked}")
except Exception:
	# Keep startup robust — don't crash if config import has issues
	import traceback
	traceback.print_exc()
sys.path.append(str(Path(__file__).parent.parent))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import (
    CORS_ALLOW_ORIGINS,
    FESTIVAL_SNAPSHOT_PREWARM_AYANAMSA,
    FESTIVAL_SNAPSHOT_PREWARM_ENABLED,
    FESTIVAL_SNAPSHOT_PREWARM_POINTS,
    FESTIVAL_SNAPSHOT_PREWARM_TZ,
    FESTIVAL_SNAPSHOT_PREWARM_YEARS,
)
from backend.services.db import ensure_content_schema
from backend.services.festival_rules_seed import seed_festival_rules
from backend.services.festivals import _year_snapshot
from backend.routers.celestial import router as celestial_router
from backend.routers.festivals import router as festivals_router
from backend.routers.horoscope import router as horoscope_router
from backend.services.locations import ensure_database
from backend.routers.locations import router as locations_router
from backend.routers.muhurat import router as muhurat_router
from backend.routers.panchang import router as panchang_router
from backend.routers.reference import router as reference_router
from backend.routers.scraper import router as scraper_router
from backend.routers.llm import router as llm_router

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
	if not FESTIVAL_SNAPSHOT_PREWARM_ENABLED:
		return

	points = _parse_prewarm_points(FESTIVAL_SNAPSHOT_PREWARM_POINTS)
	if not points:
		log.warning("Snapshot prewarm skipped: no valid points configured.")
		return

	tz       = FESTIVAL_SNAPSHOT_PREWARM_TZ
	ayanamsa = FESTIVAL_SNAPSHOT_PREWARM_AYANAMSA
	years    = [date.today().year + i for i in range(FESTIVAL_SNAPSHOT_PREWARM_YEARS)]

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

app.add_middleware(
	CORSMiddleware,
	allow_origins=CORS_ALLOW_ORIGINS,
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
app.include_router(llm_router)
