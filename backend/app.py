from fastapi import FastAPI

from services.locations import ensure_database, router as locations_router


ensure_database()

app = FastAPI(title="Panchang API", version="0.1.0")
app.include_router(locations_router)