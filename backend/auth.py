"""
Two-tier API key authentication.

  ADMIN_API_KEY — full access: scrape, LLM clean/translate, all admin endpoints.
  USER_API_KEY  — read-only access: horoscope, festivals, panchang, muhurat, etc.

Both use the standard  Authorization: Bearer <key>  header so Swagger UI's
built-in "Authorize" button works without any extra UI.

Security posture
----------------
* ADMIN_API_KEY must NEVER be embedded in the app binary. Keep it in .env /
  Render config vars and access it only via Swagger or internal tooling.
* USER_API_KEY is safe to embed in the mobile app because it is strictly
  read-only — even if someone decompiles the APK and extracts the key they
  can only read public content, nothing more.
* For stronger app-side protection add certificate pinning in Flutter (the
  http_certificate_pinning package), or integrate Android Play Integrity /
  iOS App Attest to verify requests come from a genuine unmodified app build.
"""
from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import ADMIN_API_KEY, USER_API_KEY

_bearer = HTTPBearer(
    scheme_name="BearerAuth",
    description="Paste your Admin or User API key as the Bearer token.",
    auto_error=False,
)

_MISSING_KEY = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Missing or invalid API key.",
    headers={"WWW-Authenticate": "Bearer"},
)
_ADMIN_ONLY = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Admin API key required for this operation.",
)


def _resolve_role(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if not credentials:
        return None
    token = credentials.credentials
    if ADMIN_API_KEY and token == ADMIN_API_KEY:
        return "admin"
    if USER_API_KEY and token == USER_API_KEY:
        return "user"
    return None


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    """Dependency — accepts both admin and user keys. Returns the resolved role."""
    role = _resolve_role(credentials)
    if role is None:
        raise _MISSING_KEY
    return role


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    """Dependency — accepts only the admin key."""
    role = _resolve_role(credentials)
    if role is None:
        raise _MISSING_KEY
    if role != "admin":
        raise _ADMIN_ONLY
    return role
