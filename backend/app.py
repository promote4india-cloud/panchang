from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI

from routers.locations import ensure_database, router as locations_router
from routers.muhurat import router as muhurat_router

ensure_database()

app = FastAPI(title="Panchang API", version="0.1.0")
app.include_router(locations_router)
app.include_router(muhurat_router)