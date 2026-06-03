"""
LangChain chat-model helper (replaces the old Groq-specific client).

Uses ``langchain.chat_models.init_chat_model`` with the ``provider:model``
format so the provider can be swapped by changing a single env-var.

Default provider: ``google_genai`` (Gemini).  Set ``LLM_MODEL`` in the
environment to switch, e.g.::

    LLM_MODEL=google_genai:gemini-2.0-flash      # default
    LLM_MODEL=groq:llama-3.3-70b-versatile
    LLM_MODEL=openai:gpt-4o-mini

Reads from ``backend.config`` (which loads .env via app.py at startup).

All other modules should import only from here — never import a
provider-specific SDK (groq, google-genai, openai …) directly.
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from backend.config import GEMINI_API_KEY, LLM_MODEL, LLM_SCRUB_ENABLED

log = logging.getLogger("services.llm")

# Re-export so callers can do:  from backend.services.llm import DEFAULT_MODEL
DEFAULT_MODEL: str = LLM_MODEL

# ---------------------------------------------------------------------------
# Internal singleton
# ---------------------------------------------------------------------------

_model: Optional[BaseChatModel] = None


def _parse_model_spec(spec: str) -> tuple[str, str | None]:
    """
    Split a ``provider:model`` string into *(model_name, provider)*.

    Examples
    --------
    "google_genai:gemini-2.0-flash"  → ("gemini-2.0-flash", "google_genai")
    "groq:llama-3.3-70b-versatile"   → ("llama-3.3-70b-versatile", "groq")
    "gemini-2.0-flash"               → ("gemini-2.0-flash", None)  # auto-detect
    """
    if ":" in spec:
        provider, model_name = spec.split(":", 1)
        return model_name, provider
    return spec, None


def get_chat_model() -> Optional[BaseChatModel]:
    """
    Return a shared LangChain ``BaseChatModel`` instance, or ``None`` when:
      - ``LLM_SCRUB_ENABLED`` is ``False`` (env var set to ``"0"``)
      - ``GEMINI_API_KEY`` is not set (for the default google_genai provider)
      - ``init_chat_model`` fails for any reason (logged as a warning)

    The model is initialised once and cached for the lifetime of the process.
    """
    global _model

    if not LLM_SCRUB_ENABLED:
        return None

    # For the default google_genai provider, require the API key.
    model_name, provider = _parse_model_spec(LLM_MODEL)
    resolved_provider = provider or ""
    if resolved_provider in ("google_genai", "google_vertexai", "") and not GEMINI_API_KEY:
        log.warning(
            "LLM disabled: GEMINI_API_KEY is not set "
            "(model=%r, provider=%r).",
            model_name, resolved_provider or "auto",
        )
        return None

    if _model is None:
        try:
            kwargs: dict = {}
            if resolved_provider:
                kwargs["model_provider"] = resolved_provider
            _model = init_chat_model(model=model_name, **kwargs)
            log.info(
                "LangChain chat model initialised: provider=%r model=%r",
                resolved_provider or "auto", model_name,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to initialise LangChain chat model: %s", exc)
            return None

    return _model


def is_llm_enabled() -> bool:
    """``True`` when a chat model can be obtained."""
    return get_chat_model() is not None
