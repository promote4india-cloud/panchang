"""
LLM-powered batch content cleaner.

Takes raw DB rows (fetched by the LLM router), sends prose fields to the
configured LLM in a single structured JSON prompt per batch, and writes the
cleaned text back.

Design principles:
  - One LLM API call per batch (not per field, not per record).
  - IDs, slugs, URLs, rule_json, categories — NEVER sent to the LLM.
  - If the LLM call fails for any reason, the batch is marked as an error
    and the original DB data is untouched.
  - The caller controls batch_size and rpm_limit; this module only does
    the actual cleaning.
  - Provider-agnostic: uses backend.services.llm.get_chat_model() which
    wraps LangChain's init_chat_model (default: google_genai / Gemini).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .llm import DEFAULT_MODEL, get_chat_model

log = logging.getLogger("services.content_cleaner")

# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES: list[str] = [
    "en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa", "sa", "or",
]
TARGET_LANGUAGES: list[str] = [l for l in SUPPORTED_LANGUAGES if l != "en"]

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a content editor specializing in Hindu festivals, muhurats (auspicious timings), \
horoscopes, and Vedic astrology.

Your task: clean and rephrase scraped web content. Fix grammar, remove scraper artifacts \
(e.g. trailing "More", repeated text, broken sentences), improve clarity and flow. \
Keep cultural accuracy and meaning intact. Do NOT add new information. \
Do NOT remove any factual detail. Keep the same language as the input.

You will receive a JSON object where each key maps to a text field (or a list of strings, \
or a list of [question, answer] pairs). Return a JSON object with the EXACT same keys and \
structure but with cleaned/rephrased values. Do not add commentary, just return the JSON.\
"""


_TRANSLATION_SYSTEM_PROMPT = """\
You are a professional translator specializing in Hindu festivals, muhurats, and Vedic astrology.

You will receive a JSON object where each top-level key is a record ID and its value contains \
English text fields (plain strings, lists of strings, or lists of [question, answer] pairs).

Translate ALL text values from English into these 11 languages simultaneously:
  hi (Hindi), bn (Bengali), ta (Tamil), te (Telugu), mr (Marathi),
  gu (Gujarati), kn (Kannada), ml (Malayalam), pa (Punjabi), sa (Sanskrit), or (Odia)

Translation rules:
- Preserve the JSON structure exactly — same field names, same nesting, same list shapes
- Festival/deity/Sanskrit proper nouns: render in the authentic native script \
  (e.g. "Diwali" → "दीवाली" in Hindi, "திவாலி" in Tamil)
- Keep the tone formal yet accessible, matching the cultural register of the input
- Do NOT add or remove fields; do NOT add commentary outside the JSON

Return ONLY a JSON object in this exact structure:
{
  "<record_id>": {
    "hi": { <all fields from the input, translated to Hindi> },
    "bn": { <translated to Bengali> },
    "ta": { <translated to Tamil> },
    "te": { <translated to Telugu> },
    "mr": { <translated to Marathi> },
    "gu": { <translated to Gujarati> },
    "kn": { <translated to Kannada> },
    "ml": { <translated to Malayalam> },
    "pa": { <translated to Punjabi> },
    "sa": { <translated to Sanskrit> },
    "or": { <translated to Odia> }
  }
}\
"""


# ---------------------------------------------------------------------------
# Low-level: one LLM call for a dict of prose fields
# ---------------------------------------------------------------------------

# How many times to retry on a transient error before giving up.
_MAX_RETRIES = 3


def _extract_json(text: str) -> dict[str, Any] | None:
    """
    Fallback JSON extractor for models that wrap the JSON in prose.
    Finds the first '{' and last '}' and attempts to parse what's between them.
    """
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start: end + 1])
    except json.JSONDecodeError:
        return None


async def _call_llm(
    payload: dict[str, Any],
    model: str,
    *,
    system_prompt: str = _SYSTEM_PROMPT,
) -> dict[str, Any] | None:
    """
    Send ``payload`` to the configured LangChain chat model and parse the
    JSON response.  Retries up to ``_MAX_RETRIES`` times on transient failures.
    Returns ``None`` on any unrecoverable failure.

    The ``model`` parameter is accepted for API compatibility but the actual
    model is determined by ``LLM_MODEL`` / ``init_chat_model`` at startup.
    Pass ``system_prompt`` to override the default cleaning prompt (e.g. for
    translation).
    """
    chat_model = get_chat_model()
    if chat_model is None:
        return None

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ]

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = await chat_model.ainvoke(messages)
            content = response.content if hasattr(response, "content") else response
            # Gemini (and some other providers) may return content as a list of
            # dicts/parts rather than a plain string — normalise to str.
            if isinstance(content, list):
                raw = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                ).strip()
            else:
                raw = str(content)

            if not raw.strip():
                log.warning(
                    "LLM returned empty response (attempt=%d/%d)",
                    attempt, _MAX_RETRIES,
                )
                return None

            # Primary: straight JSON parse
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass

            # Fallback: extract first {...} block (handles prose-wrapped responses)
            extracted = _extract_json(raw)
            if extracted is not None:
                log.debug("JSON extracted from prose response")
                return extracted

            log.warning(
                "LLM returned non-JSON (attempt=%d). First 300 chars: %s",
                attempt,
                raw[:300].encode("ascii", errors="replace").decode(),
            )
            return None

        except Exception as exc:  # noqa: BLE001
            err_str = str(exc)
            # Retry on common transient / rate-limit signals
            if attempt < _MAX_RETRIES and any(
                token in err_str for token in ("429", "RESOURCE_EXHAUSTED", "rate_limit", "quota")
            ):
                wait = 10.0
                log.warning(
                    "LLM rate-limit hit (attempt=%d/%d) — retrying in %.1fs: %s",
                    attempt, _MAX_RETRIES, wait, exc,
                )
                await asyncio.sleep(wait)
                continue
            log.warning("LLM call failed: %s", exc)
            return None

    return None  # exhausted retries


# ---------------------------------------------------------------------------
# Festival batch cleaner
# ---------------------------------------------------------------------------

def _build_festival_payload(rows: list[dict]) -> dict[str, Any]:
    """
    rows: list of dicts with keys from festival_content + joined rituals/faqs.
    Each entry in the batch is keyed by its festival_id.
    """
    batch: dict[str, Any] = {}
    for r in rows:
        fid = r["festival_id"]
        batch[fid] = {
            k: r[k]
            for k in ("name", "subtitle", "about", "significance",
                       "history", "scriptures", "puja_vidhi")
            if r.get(k)
        }
        if r.get("rituals"):
            batch[fid]["rituals"] = r["rituals"]   # list[str]
        if r.get("faqs"):
            batch[fid]["faqs"] = r["faqs"]          # list[[q, a]]
    return batch


async def clean_festival_batch(
    rows: list[dict],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, dict] | None:
    """
    Clean a batch of festival_content rows.
    Returns a dict keyed by festival_id → cleaned fields, or None on failure.
    """
    payload = _build_festival_payload(rows)
    if not payload:
        return {}
    return await _call_llm(payload, model)


# ---------------------------------------------------------------------------
# Muhurat batch cleaner
# ---------------------------------------------------------------------------

def _build_muhurat_payload(rows: list[dict]) -> dict[str, Any]:
    batch: dict[str, Any] = {}
    for r in rows:
        mid = r["muhurat_id"]
        batch[mid] = {
            k: r[k]
            for k in ("name", "description", "vedic_basis", "importance")
            if r.get(k)
        }
        if r.get("subsections"):
            batch[mid]["subsections"] = r["subsections"]   # list[[heading, body]]
        if r.get("faqs"):
            batch[mid]["faqs"] = r["faqs"]
    return batch


async def clean_muhurat_batch(
    rows: list[dict],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, dict] | None:
    payload = _build_muhurat_payload(rows)
    if not payload:
        return {}
    return await _call_llm(payload, model)


# ---------------------------------------------------------------------------
# Translation: English → all 11 non-English languages in one LLM call
# ---------------------------------------------------------------------------

async def translate_festival_batch(
    en_rows: list[dict],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, dict[str, dict]] | None:
    """
    Translate a batch of cleaned English festival_content rows into all 11
    non-English target languages in a single LLM call.

    Returns {festival_id: {lang_code: {field: value}}} or None on failure.
    """
    payload = _build_festival_payload(en_rows)
    if not payload:
        return {}
    return await _call_llm(payload, model, system_prompt=_TRANSLATION_SYSTEM_PROMPT)


async def translate_muhurat_batch(
    en_rows: list[dict],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, dict[str, dict]] | None:
    """
    Translate a batch of cleaned English muhurat_content rows into all 11
    non-English target languages in a single LLM call.

    Returns {muhurat_id: {lang_code: {field: value}}} or None on failure.
    """
    payload = _build_muhurat_payload(en_rows)
    if not payload:
        return {}
    return await _call_llm(payload, model, system_prompt=_TRANSLATION_SYSTEM_PROMPT)


# ---------------------------------------------------------------------------
# Horoscope batch cleaner
# ---------------------------------------------------------------------------

_HOROSCOPE_PROSE_FIELDS = (
    "prediction", "love", "career", "finance", "health", "family", "advice",
)


def _build_horoscope_payload(rows: list[dict]) -> dict[str, Any]:
    batch: dict[str, Any] = {}
    for r in rows:
        # Composite key so we can match rows back after cleaning
        key = f"{r['sign']}|{r['period']}|{r['language']}|{r['period_key']}"
        entry = {k: r[k] for k in _HOROSCOPE_PROSE_FIELDS if r.get(k)}
        if entry:
            batch[key] = entry
    return batch


async def clean_horoscope_batch(
    rows: list[dict],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, dict] | None:
    payload = _build_horoscope_payload(rows)
    if not payload:
        return {}
    return await _call_llm(payload, model)


async def translate_horoscope_batch(
    en_rows: list[dict],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, dict[str, dict]] | None:
    """
    Translate a batch of cleaned English horoscope rows into all 11
    non-English target languages in a single LLM call.

    Returns {composite_key: {lang_code: {field: value}}} or None on failure.
    """
    payload = _build_horoscope_payload(en_rows)
    if not payload:
        return {}
    return await _call_llm(payload, model, system_prompt=_TRANSLATION_SYSTEM_PROMPT)


# ---------------------------------------------------------------------------
# Zodiac sign deep-dive batch cleaner
# ---------------------------------------------------------------------------

_DEEPDIVE_PROSE_FIELDS = (
    "summary", "traits", "love", "compatibility",
    "overview", "physical_appearance", "mental_ability",
    "characteristics", "aspects_of_life", "twelve_houses",
)


def _build_deepdive_payload(rows: list[dict]) -> dict[str, Any]:
    batch: dict[str, Any] = {}
    for r in rows:
        key = f"{r['id']}|{r['language']}"
        entry = {k: r[k] for k in _DEEPDIVE_PROSE_FIELDS if r.get(k)}
        if entry:
            batch[key] = entry
    return batch


async def clean_deepdive_batch(
    rows: list[dict],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, dict] | None:
    payload = _build_deepdive_payload(rows)
    if not payload:
        return {}
    return await _call_llm(payload, model)


# ---------------------------------------------------------------------------
# RPM-aware rate limiter
# ---------------------------------------------------------------------------

class RpmLimiter:
    """Token-bucket style per-minute rate limiter for Groq API calls."""

    def __init__(self, rpm: int) -> None:
        self._interval = 60.0 / max(rpm, 1)
        self._last: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = self._interval - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = asyncio.get_event_loop().time()
