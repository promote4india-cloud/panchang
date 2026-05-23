from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI

from backend.services.db import ensure_content_schema
from backend.services.festival_rules_seed import seed_festival_rules
from backend.routers.celestial import router as celestial_router
from backend.routers.festivals import router as festivals_router
from backend.routers.locations import ensure_database, router as locations_router
from backend.routers.muhurat import router as muhurat_router
from backend.routers.panchang import router as panchang_router
from backend.routers.reference import router as reference_router
from backend.routers.scraper import router as scraper_router

ensure_database()           # GeoNames build (only on first run)
ensure_content_schema()     # additive editorial tables — safe on every boot
seed_festival_rules()       # apply curated festival rule catalog (idempotent)

app = FastAPI(title="Panchang API", version="0.1.0")
app.include_router(locations_router)
app.include_router(muhurat_router)
app.include_router(panchang_router)
app.include_router(celestial_router)
app.include_router(reference_router)
app.include_router(festivals_router)
app.include_router(scraper_router)