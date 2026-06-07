"""
Central configuration — all environment variables in one place.

Reads from the .env file in the backend directory (via load_dotenv called in
app.py at startup) or from the actual process environment in production.
All other modules should import from here instead of calling os.getenv directly.
"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# LLM Cleaning Layer  (LangChain-based, provider-agnostic)
# ---------------------------------------------------------------------------

#: Set to "0" to disable the LLM cleaning layer entirely.
LLM_SCRUB_ENABLED: bool = os.getenv("LLM_SCRUB_ENABLED", "1") != "0"

#: Gemini API key — https://aistudio.google.com/app/apikey
#: Used by the default ``google_genai`` provider.
#: langchain-google-genai also picks this up automatically from the env.
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

#: Active LLM model in ``provider:model`` format (used by init_chat_model).
#:
#: Examples:
#:   google_genai:gemini-2.0-flash          — Gemini 2.0 Flash (default)
#:   google_genai:gemini-1.5-pro            — Gemini 1.5 Pro
#:   groq:llama-3.3-70b-versatile           — Groq via LangChain
#:   openai:gpt-4o-mini                     — OpenAI via LangChain
LLM_MODEL: str = os.getenv("LLM_MODEL", "google_genai:gemini-2.0-flash")

# ---------------------------------------------------------------------------
# Backward-compat aliases (kept so existing .env files don't break)
# ---------------------------------------------------------------------------

#: Deprecated — prefer GEMINI_API_KEY / LLM_MODEL.
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")

#: Deprecated — prefer LLM_MODEL.
GROQ_MODEL: str = os.getenv("GROQ_MODEL", LLM_MODEL)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

#: PostgreSQL connection string — set automatically by Render when a Postgres
#: database is linked, or manually via DATABASE_URL in .env for local dev.
#: Format: postgresql://user:password@host:5432/dbname
DATABASE_URL: str | None = os.getenv("DATABASE_URL")

# ---------------------------------------------------------------------------
# API Authentication
# ---------------------------------------------------------------------------

#: Full-access key — admin operations (scrape, LLM clean/translate).
#: Must NEVER be embedded in the mobile app binary.
ADMIN_API_KEY: str | None = os.getenv("ADMIN_API_KEY")

#: Read-only key — content endpoints (horoscope, festivals, panchang, …).
#: Safe to embed in the app; grants no write or admin access.
USER_API_KEY: str | None = os.getenv("USER_API_KEY")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

#: Comma-separated list of allowed origins for CORS middleware.
CORS_ALLOW_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

#: Optional regex for allowed origins (useful for localhost with dynamic ports).
CORS_ALLOW_ORIGIN_REGEX: str | None = os.getenv(
    "CORS_ALLOW_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
)

# ---------------------------------------------------------------------------
# Heartbeat — keep-alive ping for Render free tier
# ---------------------------------------------------------------------------

#: URL to GET on each heartbeat tick.  Defaults to <RENDER_EXTERNAL_URL>/health
#: when running on Render (that env-var is injected automatically).
#: Set to "" to disable.
_render_base: str = os.getenv("RENDER_EXTERNAL_URL", "")
HEARTBEAT_URL: str = os.getenv(
    "HEARTBEAT_URL",
    f"{_render_base}/health" if _render_base else "",
)

#: Seconds between heartbeat pings.  Render free tier sleeps after 15 min of
#: inactivity, so 600 s (10 min) gives comfortable headroom.
try:
    HEARTBEAT_INTERVAL: int = max(60, int(os.getenv("HEARTBEAT_INTERVAL", "600")))
except ValueError:
    HEARTBEAT_INTERVAL = 600

# ---------------------------------------------------------------------------
# Festival snapshot prewarming
# ---------------------------------------------------------------------------

#: Set to "0" to skip prewarming on startup.
FESTIVAL_SNAPSHOT_PREWARM_ENABLED: bool = (
    os.getenv("FESTIVAL_SNAPSHOT_PREWARM_ENABLED", "1") == "1"
)

#: Semicolon-separated "lat:lon" pairs to prewarm.
FESTIVAL_SNAPSHOT_PREWARM_POINTS: str = os.getenv(
    "FESTIVAL_SNAPSHOT_PREWARM_POINTS",
    "28.6139:77.2090;19.0760:72.8777;13.0827:80.2707;22.5726:88.3639",
)

#: How many years ahead to prewarm (default: current year only).
try:
    FESTIVAL_SNAPSHOT_PREWARM_YEARS: int = max(
        1, int(os.getenv("FESTIVAL_SNAPSHOT_PREWARM_YEARS", "5"))
    )
except ValueError:
    FESTIVAL_SNAPSHOT_PREWARM_YEARS = 1


#: Timezone string for prewarm calculations.
FESTIVAL_SNAPSHOT_PREWARM_TZ: str = os.getenv(
    "FESTIVAL_SNAPSHOT_PREWARM_TZ", "Asia/Kolkata"
)

#: Ayanamsa for prewarm calculations.
FESTIVAL_SNAPSHOT_PREWARM_AYANAMSA: str = os.getenv(
    "FESTIVAL_SNAPSHOT_PREWARM_AYANAMSA", "lahiri"
)
