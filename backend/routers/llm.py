"""
LLM content-cleaning endpoints.

All four POST endpoints kick off a background clean job and return
immediately with a job_id. Use GET /v1/admin/llm/jobs/{job_id} to poll
progress, and GET /v1/admin/llm/jobs to list recent jobs.

  POST /v1/admin/llm/clean/festivals
  POST /v1/admin/llm/clean/muhurats
  POST /v1/admin/llm/clean/horoscope
  POST /v1/admin/llm/clean/sign-deepdive

Common request body (LLMCleanRequest):
  model       Groq model name (default: compound-beta)
  batch_size  Records per API call (default: 5, max: 20)
  rpm_limit   Max Groq calls per minute (default: 25)
  language    Filter rows by language — None means all languages
  force       If true, re-clean rows that already have llm_cleaned_at set
  limit       Cap total records processed in this run (None = no cap)
  dry_run     Preview LLM output without writing to DB
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.auth import require_admin

from backend.services.content_cleaner import (
    RpmLimiter,
    TARGET_LANGUAGES,
    clean_deepdive_batch,
    clean_festival_batch,
    clean_horoscope_batch,
    clean_muhurat_batch,
    translate_festival_batch,
    translate_horoscope_batch,
    translate_muhurat_batch,
)
from backend.services.db import connect_ro, connect_rw
from backend.services.llm import DEFAULT_MODEL, is_llm_enabled

log = logging.getLogger("routers.llm")


# ---------------------------------------------------------------------------
# Terminal printer — always visible in uvicorn regardless of log level.
# Uses ANSI colours: cyan=info, yellow=warn, green=ok, red=error, dim=detail.
# ---------------------------------------------------------------------------

_RESET  = "\033[0m"
_CYAN   = "\033[36m"
_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_RED    = "\033[31m"
_DIM    = "\033[2m"
_BOLD   = "\033[1m"


def _cprint(level: str, job_id: str, msg: str) -> None:
    """Coloured, timestamped print that always appears on the uvicorn console."""
    from datetime import datetime
    ts  = datetime.now().strftime("%H:%M:%S")
    jid = job_id[:8]          # first 8 hex chars are enough for readability
    colour = {
        "INFO":  _CYAN,
        "OK":    _GREEN,
        "WARN":  _YELLOW,
        "ERROR": _RED,
    }.get(level, _DIM)
    print(
        f"{_DIM}{ts}{_RESET} "
        f"{colour}{_BOLD}[LLM/{level}]{_RESET} "
        f"{_DIM}job={jid}{_RESET} "
        f"{msg}",
        flush=True,
    )

router = APIRouter(
    prefix="/v1/admin/llm",
    tags=["admin-llm"],
    dependencies=[Depends(require_admin)],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class LLMCleanRequest(BaseModel):
    batch_size: int = Field(3, ge=1, le=20, description="Records per API call")
    rpm_limit: int = Field(30, ge=1, le=60, description="Max LLM calls per minute")
    language: Optional[str] = Field(
        None,
        description="Filter by language code e.g. 'en', 'hi'. Leave empty for all.",
    )
    force: bool = Field(False, description="Re-clean already-cleaned rows")
    limit: Optional[int] = Field(None, ge=1, description="Max records to process")
    dry_run: bool = Field(False, description="Preview output without writing to DB")

    @field_validator("language", mode="before")
    @classmethod
    def _clean_language(cls, v):
        """Reject Swagger placeholder values and strip whitespace."""
        if v is None:
            return None
        v = str(v).strip().lower()
        # Common Swagger/OpenAPI placeholder strings — treat as 'no filter'
        if v in ("", "string", "null", "none", "undefined"):
            return None
        if len(v) > 10:  # language codes are 2-5 chars
            raise ValueError(f"Invalid language code: {v!r}")
        return v


# ---------------------------------------------------------------------------
# In-process LLM job tracking
# ---------------------------------------------------------------------------

@dataclass
class LLMJob:
    id: str
    category: str          # 'festivals'|'muhurats'|'horoscope'|'sign-deepdive'
    model: str
    dry_run: bool
    status: str = "running"  # running|completed|cancelled|failed
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    note: Optional[str] = None
    counters: dict[str, int] = field(default_factory=lambda: {
        "fetched": 0, "cleaned": 0, "skipped": 0, "errors": 0, "written": 0,
    })
    task: Optional[asyncio.Task] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "model": self.model,
            "dry_run": self.dry_run,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "note": self.note,
            "counters": dict(self.counters),
        }


class LLMJobManager:
    """Singleton — one LLM clean job at a time per category."""
    _jobs: dict[str, LLMJob] = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, *, category: str, model: str, dry_run: bool,
               runner) -> LLMJob:
        job = LLMJob(id=uuid4().hex, category=category, model=model, dry_run=dry_run)
        with cls._lock:
            cls._jobs[job.id] = job
        job.task = asyncio.create_task(_wrap_llm_job(job, runner))
        return job

    @classmethod
    def get(cls, job_id: str) -> Optional[LLMJob]:
        return cls._jobs.get(job_id)

    @classmethod
    def list_recent(cls, limit: int = 20) -> list[LLMJob]:
        jobs = sorted(cls._jobs.values(),
                      key=lambda j: j.started_at, reverse=True)
        return jobs[:limit]

    @classmethod
    def cancel(cls, job_id: str) -> bool:
        job = cls._jobs.get(job_id)
        if job and job.status == "running" and job.task:
            job.task.cancel()
            return True
        return False


async def _wrap_llm_job(job: LLMJob, runner) -> None:
    _cprint("INFO", job.id,
            f"Starting {_BOLD}{job.category}{_RESET} clean "
            f"| model={job.model} dry_run={job.dry_run}")
    try:
        await runner(job)
        job.status = "completed"
        c = job.counters
        _cprint("OK", job.id,
                f"Done — fetched={c['fetched']} cleaned={c['cleaned']} "
                f"written={c['written']} skipped={c['skipped']} errors={c['errors']}")
    except asyncio.CancelledError:
        job.status = "cancelled"
        _cprint("WARN", job.id, "Job cancelled by user")
        log.info("LLM job %s cancelled", job.id)
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.note = f"{type(exc).__name__}: {exc}"
        _cprint("ERROR", job.id, f"Job FAILED: {exc}")
        log.exception("LLM job %s failed", job.id)
    finally:
        job.finished_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Runner helpers — one per category
# ---------------------------------------------------------------------------

def _make_festival_runner(req: LLMCleanRequest):
    async def _run(job: LLMJob) -> None:
        limiter = RpmLimiter(req.rpm_limit)

        # Fetch uncleaned festival_content rows (with joined rituals + faqs)
        conn = connect_ro()
        try:
            # Only rows with at least one prose column populated.
            # festival_rules_seed creates 159 stub rows with all prose = NULL —
            # those have nothing for the LLM to clean.
            sql = """
                SELECT fc.festival_id, fc.language, fc.name, fc.subtitle,
                       fc.about, fc.significance, fc.history,
                       fc.scriptures, fc.puja_vidhi
                FROM festival_content fc
                WHERE (
                    fc.about IS NOT NULL OR
                    fc.significance IS NOT NULL OR fc.history IS NOT NULL OR
                    fc.scriptures IS NOT NULL OR fc.puja_vidhi IS NOT NULL
                )
            """
            params: list[Any] = []
            if not req.force:
                sql += " AND (fc.llm_cleaned_at IS NULL)"
            if req.language:
                sql += " AND fc.language = %s"
                params.append(req.language)
            if req.limit:
                sql += f" LIMIT {req.limit}"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()


        job.counters["fetched"] = len(rows)
        if not rows:
            _cprint("WARN", job.id,
                    "No festival_content rows found "
                    f"(force={req.force} language={req.language!r}). "
                    "Run the crawl first or pass force=true.")
            return

        _cprint("INFO", job.id,
                f"Fetched {len(rows)} festival rows "
                f"| batch_size={req.batch_size} rpm_limit={req.rpm_limit}")

        # Attach rituals and faqs for each row
        for row in rows:
            conn = connect_ro()
            try:
                row["rituals"] = [
                    r["text"] for r in conn.execute(
                        "SELECT text FROM festival_rituals "
                        "WHERE festival_id=%s AND language=%s ORDER BY position",
                        (row["festival_id"], row["language"]),
                    ).fetchall()
                ]
                row["faqs"] = [
                    [r["question"], r["answer"]] for r in conn.execute(
                        "SELECT question, answer FROM festival_faqs "
                        "WHERE festival_id=%s AND language=%s ORDER BY position",
                        (row["festival_id"], row["language"]),
                    ).fetchall()
                ]
            finally:
                conn.close()

        total_batches = (len(rows) + req.batch_size - 1) // req.batch_size

        # Process in batches
        for batch_num, i in enumerate(range(0, len(rows), req.batch_size), start=1):
            batch = rows[i: i + req.batch_size]
            ids   = ", ".join(r["festival_id"] for r in batch)
            _cprint("INFO", job.id,
                    f"Batch {batch_num}/{total_batches} "
                    f"({len(batch)} records) → calling LLM ... "
                    f"{_DIM}[{ids}]{_RESET}")

            await limiter.acquire()
            cleaned = await clean_festival_batch(batch, model=DEFAULT_MODEL)

            if cleaned is None:
                job.counters["errors"] += len(batch)
                _cprint("ERROR", job.id,
                        f"Batch {batch_num}/{total_batches} FAILED (LLM error) — skipping")
                continue

            job.counters["cleaned"] += len(cleaned)
            _cprint("OK", job.id,
                    f"Batch {batch_num}/{total_batches} cleaned "
                    f"({len(cleaned)} records returned by LLM)")

            if req.dry_run:
                job.counters["skipped"] += len(batch)
                _cprint("WARN", job.id,
                        f"dry_run=true — batch {batch_num} NOT written to DB")
                continue

            # Write cleaned fields back to DB
            conn = connect_rw()
            written_this_batch = 0
            try:
                for row in batch:
                    fid  = row["festival_id"]
                    lang = row["language"]
                    c    = cleaned.get(fid, {})
                    if not c:
                        _cprint("WARN", job.id,
                                f"LLM returned no entry for festival_id={fid!r} — skipping")
                        continue

                    conn.execute(
                        """
                        UPDATE festival_content SET
                            name        = COALESCE(%s, name),
                            subtitle    = COALESCE(%s, subtitle),
                            about       = COALESCE(%s, about),
                            significance= COALESCE(%s, significance),
                            history     = COALESCE(%s, history),
                            scriptures  = COALESCE(%s, scriptures),
                            puja_vidhi  = COALESCE(%s, puja_vidhi),
                            llm_cleaned_at = NOW()
                        WHERE festival_id=%s AND language=%s
                        """,
                        (
                            c.get("name"), c.get("subtitle"), c.get("about"),
                            c.get("significance"), c.get("history"),
                            c.get("scriptures"), c.get("puja_vidhi"),
                            fid, lang,
                        ),
                    )

                    if "rituals" in c and isinstance(c["rituals"], list):
                        conn.execute(
                            "DELETE FROM festival_rituals "
                            "WHERE festival_id=%s AND language=%s", (fid, lang),
                        )
                        with conn.cursor() as _cur:
                            _cur.executemany(
                                "INSERT INTO festival_rituals VALUES (%s,%s,%s,%s)",
                                [(fid, lang, pos, txt)
                                 for pos, txt in enumerate(c["rituals"])],
                            )

                    if "faqs" in c and isinstance(c["faqs"], list):
                        conn.execute(
                            "DELETE FROM festival_faqs "
                            "WHERE festival_id=%s AND language=%s", (fid, lang),
                        )
                        with conn.cursor() as _cur:
                            _cur.executemany(
                                "INSERT INTO festival_faqs VALUES (%s,%s,%s,%s,%s)",
                                [(fid, lang, pos, qa[0], qa[1])
                                 for pos, qa in enumerate(c["faqs"])
                                 if isinstance(qa, (list, tuple)) and len(qa) == 2],
                            )

                    job.counters["written"] += 1
                    written_this_batch += 1

                conn.commit()
                _cprint("OK", job.id,
                        f"Batch {batch_num}/{total_batches} written "
                        f"({written_this_batch} rows committed)")
            finally:
                conn.close()

    return _run


def _make_muhurat_runner(req: LLMCleanRequest):
    async def _run(job: LLMJob) -> None:
        limiter = RpmLimiter(req.rpm_limit)

        conn = connect_ro()
        try:
            sql = """
                SELECT mc.muhurat_id, mc.language, mc.name, mc.description,
                       mc.vedic_basis, mc.importance
                FROM muhurat_content mc
                WHERE 1=1
            """
            params: list[Any] = []
            if not req.force:
                sql += " AND (mc.llm_cleaned_at IS NULL)"
            if req.language:
                sql += " AND mc.language = %s"
                params.append(req.language)
            if req.limit:
                sql += f" LIMIT {req.limit}"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

        job.counters["fetched"] = len(rows)
        if not rows:
            _cprint("WARN", job.id,
                    "No muhurat_content rows found "
                    f"(force={req.force} language={req.language!r}). "
                    "Run the crawl first or pass force=true.")
            return

        _cprint("INFO", job.id,
                f"Fetched {len(rows)} muhurat rows "
                f"| batch_size={req.batch_size} rpm_limit={req.rpm_limit}")

        # Attach subsections and faqs
        for row in rows:
            conn = connect_ro()
            try:
                row["subsections"] = [
                    [r["heading"] or "", r["body"]] for r in conn.execute(
                        "SELECT heading, body FROM muhurat_subsections "
                        "WHERE muhurat_id=%s AND language=%s AND body IS NOT NULL ORDER BY position",
                        (row["muhurat_id"], row["language"]),
                    ).fetchall()
                ]
                row["faqs"] = [
                    [r["question"], r["answer"]] for r in conn.execute(
                        "SELECT question, answer FROM muhurat_faqs "
                        "WHERE muhurat_id=%s AND language=%s ORDER BY position",
                        (row["muhurat_id"], row["language"]),
                    ).fetchall()
                ]
            finally:
                conn.close()

        total_batches = (len(rows) + req.batch_size - 1) // req.batch_size

        for batch_num, i in enumerate(range(0, len(rows), req.batch_size), start=1):
            batch = rows[i: i + req.batch_size]
            ids   = ", ".join(r["muhurat_id"] for r in batch)
            _cprint("INFO", job.id,
                    f"Batch {batch_num}/{total_batches} "
                    f"({len(batch)} records) → calling LLM ... "
                    f"{_DIM}[{ids}]{_RESET}")

            await limiter.acquire()
            cleaned = await clean_muhurat_batch(batch, model=DEFAULT_MODEL)

            if cleaned is None:
                job.counters["errors"] += len(batch)
                _cprint("ERROR", job.id,
                        f"Batch {batch_num}/{total_batches} FAILED — skipping")
                continue

            job.counters["cleaned"] += len(cleaned)
            _cprint("OK", job.id,
                    f"Batch {batch_num}/{total_batches} cleaned ({len(cleaned)} records)")

            if req.dry_run:
                job.counters["skipped"] += len(batch)
                _cprint("WARN", job.id, f"dry_run=true — batch {batch_num} NOT written")
                continue

            conn = connect_rw()
            written_this_batch = 0
            try:
                for row in batch:
                    mid  = row["muhurat_id"]
                    lang = row["language"]
                    c    = cleaned.get(mid, {})
                    if not c:
                        _cprint("WARN", job.id,
                                f"No LLM entry for muhurat_id={mid!r} — skipping")
                        continue

                    conn.execute(
                        """
                        UPDATE muhurat_content SET
                            name        = COALESCE(%s, name),
                            description = COALESCE(%s, description),
                            vedic_basis = COALESCE(%s, vedic_basis),
                            importance  = COALESCE(%s, importance),
                            llm_cleaned_at = NOW()
                        WHERE muhurat_id=%s AND language=%s
                        """,
                        (
                            c.get("name"), c.get("description"),
                            c.get("vedic_basis"), c.get("importance"),
                            mid, lang,
                        ),
                    )

                    if "subsections" in c and isinstance(c["subsections"], list):
                        conn.execute(
                            "DELETE FROM muhurat_subsections "
                            "WHERE muhurat_id=%s AND language=%s", (mid, lang),
                        )
                        with conn.cursor() as _cur:
                            _cur.executemany(
                                "INSERT INTO muhurat_subsections VALUES (%s,%s,%s,%s,%s)",
                                [(mid, lang, pos, ss[0], ss[1])
                                 for pos, ss in enumerate(c["subsections"])
                                 if isinstance(ss, (list, tuple)) and len(ss) == 2],
                            )

                    if "faqs" in c and isinstance(c["faqs"], list):
                        conn.execute(
                            "DELETE FROM muhurat_faqs "
                            "WHERE muhurat_id=%s AND language=%s", (mid, lang),
                        )
                        with conn.cursor() as _cur:
                            _cur.executemany(
                                "INSERT INTO muhurat_faqs VALUES (%s,%s,%s,%s,%s)",
                                [(mid, lang, pos, qa[0], qa[1])
                                 for pos, qa in enumerate(c["faqs"])
                                 if isinstance(qa, (list, tuple)) and len(qa) == 2],
                            )

                    job.counters["written"] += 1
                    written_this_batch += 1

                conn.commit()
                _cprint("OK", job.id,
                        f"Batch {batch_num}/{total_batches} written "
                        f"({written_this_batch} rows committed)")
            finally:
                conn.close()

    return _run


def _make_horoscope_runner(req: LLMCleanRequest):
    async def _run(job: LLMJob) -> None:
        limiter = RpmLimiter(req.rpm_limit)

        conn = connect_ro()
        try:
            sql = """
                SELECT sign, period, language, period_key,
                       prediction, love, career, finance, health, family, advice
                FROM horoscope_predictions
                WHERE 1=1
            """
            params: list[Any] = []
            if not req.force:
                sql += " AND (llm_cleaned_at IS NULL)"
            if req.language:
                sql += " AND language = %s"
                params.append(req.language)
            if req.limit:
                sql += f" LIMIT {req.limit}"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

        job.counters["fetched"] = len(rows)
        if not rows:
            _cprint("WARN", job.id,
                    "No horoscope_predictions rows found "
                    f"(force={req.force} language={req.language!r}). "
                    "Fetch a horoscope first or pass force=true.")
            return

        _cprint("INFO", job.id,
                f"Fetched {len(rows)} horoscope rows "
                f"| batch_size={req.batch_size} rpm_limit={req.rpm_limit}")

        total_batches = (len(rows) + req.batch_size - 1) // req.batch_size

        for batch_num, i in enumerate(range(0, len(rows), req.batch_size), start=1):
            batch = rows[i: i + req.batch_size]
            ids   = ", ".join(
                f"{r['sign']}/{r['period']}/{r['period_key']}" for r in batch
            )
            _cprint("INFO", job.id,
                    f"Batch {batch_num}/{total_batches} "
                    f"({len(batch)} records) → calling LLM ... "
                    f"{_DIM}[{ids}]{_RESET}")

            await limiter.acquire()
            cleaned = await clean_horoscope_batch(batch, model=DEFAULT_MODEL)

            if cleaned is None:
                job.counters["errors"] += len(batch)
                _cprint("ERROR", job.id,
                        f"Batch {batch_num}/{total_batches} FAILED — skipping")
                continue

            job.counters["cleaned"] += len(cleaned)
            _cprint("OK", job.id,
                    f"Batch {batch_num}/{total_batches} cleaned ({len(cleaned)} records)")

            if req.dry_run:
                job.counters["skipped"] += len(batch)
                _cprint("WARN", job.id, f"dry_run=true — batch {batch_num} NOT written")
                continue

            conn = connect_rw()
            written_this_batch = 0
            try:
                for row in batch:
                    composite_key = (
                        f"{row['sign']}|{row['period']}|"
                        f"{row['language']}|{row['period_key']}"
                    )
                    c = cleaned.get(composite_key, {})
                    if not c:
                        _cprint("WARN", job.id,
                                f"No LLM entry for {composite_key!r} — skipping")
                        continue

                    conn.execute(
                        """
                        UPDATE horoscope_predictions SET
                            prediction = COALESCE(%s, prediction),
                            love       = COALESCE(%s, love),
                            career     = COALESCE(%s, career),
                            finance    = COALESCE(%s, finance),
                            health     = COALESCE(%s, health),
                            family     = COALESCE(%s, family),
                            advice     = COALESCE(%s, advice),
                            llm_cleaned_at = NOW()
                        WHERE sign=%s AND period=%s AND language=%s AND period_key=%s
                        """,
                        (
                            c.get("prediction"), c.get("love"), c.get("career"),
                            c.get("finance"), c.get("health"), c.get("family"),
                            c.get("advice"),
                            row["sign"], row["period"],
                            row["language"], row["period_key"],
                        ),
                    )
                    job.counters["written"] += 1
                    written_this_batch += 1

                conn.commit()
                _cprint("OK", job.id,
                        f"Batch {batch_num}/{total_batches} written "
                        f"({written_this_batch} rows committed)")
            finally:
                conn.close()

    return _run


def _make_deepdive_runner(req: LLMCleanRequest):
    async def _run(job: LLMJob) -> None:
        limiter = RpmLimiter(req.rpm_limit)

        conn = connect_ro()
        try:
            sql = """
                SELECT id, language, summary, traits, love, compatibility,
                       overview, physical_appearance, mental_ability,
                       characteristics, aspects_of_life, twelve_houses
                FROM zodiac_signs
                WHERE 1=1
            """
            params: list[Any] = []
            if not req.force:
                sql += " AND (llm_cleaned_at IS NULL)"
            if req.language:
                sql += " AND language = %s"
                params.append(req.language)
            if req.limit:
                sql += f" LIMIT {req.limit}"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

        job.counters["fetched"] = len(rows)
        if not rows:
            _cprint("WARN", job.id,
                    "No zodiac_signs rows found "
                    f"(force={req.force} language={req.language!r}). "
                    "Fetch a daily horoscope or sign intro first.")
            return

        _cprint("INFO", job.id,
                f"Fetched {len(rows)} zodiac_signs rows "
                f"| batch_size={req.batch_size} rpm_limit={req.rpm_limit}")

        total_batches = (len(rows) + req.batch_size - 1) // req.batch_size

        for batch_num, i in enumerate(range(0, len(rows), req.batch_size), start=1):
            batch = rows[i: i + req.batch_size]
            ids   = ", ".join(r["id"] for r in batch)
            _cprint("INFO", job.id,
                    f"Batch {batch_num}/{total_batches} "
                    f"({len(batch)} records) → calling LLM ... "
                    f"{_DIM}[{ids}]{_RESET}")

            await limiter.acquire()
            cleaned = await clean_deepdive_batch(batch, model=DEFAULT_MODEL)

            if cleaned is None:
                job.counters["errors"] += len(batch)
                _cprint("ERROR", job.id,
                        f"Batch {batch_num}/{total_batches} FAILED — skipping")
                continue

            job.counters["cleaned"] += len(cleaned)
            _cprint("OK", job.id,
                    f"Batch {batch_num}/{total_batches} cleaned ({len(cleaned)} records)")

            if req.dry_run:
                job.counters["skipped"] += len(batch)
                _cprint("WARN", job.id, f"dry_run=true — batch {batch_num} NOT written")
                continue

            conn = connect_rw()
            written_this_batch = 0
            try:
                for row in batch:
                    key = f"{row['id']}|{row['language']}"
                    c   = cleaned.get(key, {})
                    if not c:
                        _cprint("WARN", job.id,
                                f"No LLM entry for zodiac key={key!r} — skipping")
                        continue

                    conn.execute(
                        """
                        UPDATE zodiac_signs SET
                            summary             = COALESCE(%s, summary),
                            traits              = COALESCE(%s, traits),
                            love                = COALESCE(%s, love),
                            compatibility       = COALESCE(%s, compatibility),
                            overview            = COALESCE(%s, overview),
                            physical_appearance = COALESCE(%s, physical_appearance),
                            mental_ability      = COALESCE(%s, mental_ability),
                            characteristics     = COALESCE(%s, characteristics),
                            aspects_of_life     = COALESCE(%s, aspects_of_life),
                            twelve_houses       = COALESCE(%s, twelve_houses),
                            llm_cleaned_at      = NOW()
                        WHERE id=%s AND language=%s
                        """,
                        (
                            c.get("summary"), c.get("traits"),
                            c.get("love"), c.get("compatibility"),
                            c.get("overview"), c.get("physical_appearance"),
                            c.get("mental_ability"), c.get("characteristics"),
                            c.get("aspects_of_life"), c.get("twelve_houses"),
                            row["id"], row["language"],
                        ),
                    )
                    job.counters["written"] += 1
                    written_this_batch += 1

                conn.commit()
                _cprint("OK", job.id,
                        f"Batch {batch_num}/{total_batches} written "
                        f"({written_this_batch} rows committed)")
            finally:
                conn.close()

    return _run


# ---------------------------------------------------------------------------
# Translation runners: English → 11 non-English languages
# ---------------------------------------------------------------------------

def _make_festival_translate_runner(req: LLMCleanRequest):
    async def _run(job: LLMJob) -> None:
        limiter = RpmLimiter(req.rpm_limit)

        conn = connect_ro()
        try:
            sql = """
                SELECT fc.festival_id, fc.language, fc.name, fc.subtitle,
                       fc.about, fc.significance, fc.history,
                       fc.scriptures, fc.puja_vidhi, fc.source_url
                FROM festival_content fc
                WHERE fc.language = 'en'
                  AND (
                    fc.about IS NOT NULL OR fc.significance IS NOT NULL OR
                    fc.history IS NOT NULL OR fc.scriptures IS NOT NULL OR
                    fc.puja_vidhi IS NOT NULL
                  )
            """
            params: list[Any] = []
            if not req.force:
                # Only process festivals that have no non-English rows yet.
                sql += """
                  AND NOT EXISTS (
                    SELECT 1 FROM festival_content fc2
                    WHERE fc2.festival_id = fc.festival_id AND fc2.language != 'en'
                  )
                """
            if req.limit:
                sql += f" LIMIT {req.limit}"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

        job.counters["fetched"] = len(rows)
        if not rows:
            _cprint("WARN", job.id,
                    "No English festival rows pending translation "
                    f"(force={req.force}). Run clean/festivals first, "
                    "or pass force=true to re-translate.")
            return

        _cprint("INFO", job.id,
                f"Fetched {len(rows)} English festival rows → translating to "
                f"{len(TARGET_LANGUAGES)} languages "
                f"| batch_size={req.batch_size} rpm_limit={req.rpm_limit}")

        # Attach English rituals and faqs as source content
        for row in rows:
            conn = connect_ro()
            try:
                row["rituals"] = [
                    r["text"] for r in conn.execute(
                        "SELECT text FROM festival_rituals "
                        "WHERE festival_id=%s AND language='en' ORDER BY position",
                        (row["festival_id"],),
                    ).fetchall()
                ]
                row["faqs"] = [
                    [r["question"], r["answer"]] for r in conn.execute(
                        "SELECT question, answer FROM festival_faqs "
                        "WHERE festival_id=%s AND language='en' ORDER BY position",
                        (row["festival_id"],),
                    ).fetchall()
                ]
            finally:
                conn.close()

        total_batches = (len(rows) + req.batch_size - 1) // req.batch_size

        for batch_num, i in enumerate(range(0, len(rows), req.batch_size), start=1):
            batch = rows[i: i + req.batch_size]
            ids = ", ".join(r["festival_id"] for r in batch)
            _cprint("INFO", job.id,
                    f"Batch {batch_num}/{total_batches} "
                    f"({len(batch)} records) → translating ... "
                    f"{_DIM}[{ids}]{_RESET}")

            await limiter.acquire()
            translated = await translate_festival_batch(batch, model=DEFAULT_MODEL)

            if translated is None:
                job.counters["errors"] += len(batch)
                _cprint("ERROR", job.id,
                        f"Batch {batch_num}/{total_batches} FAILED (LLM error) — skipping")
                continue

            job.counters["cleaned"] += len(translated)
            _cprint("OK", job.id,
                    f"Batch {batch_num}/{total_batches} translated ({len(translated)} festivals)")

            if req.dry_run:
                job.counters["skipped"] += len(batch)
                _cprint("WARN", job.id,
                        f"dry_run=true — batch {batch_num} NOT written to DB")
                continue

            conn = connect_rw()
            written_this_batch = 0
            try:
                for row in batch:
                    fid = row["festival_id"]
                    lang_map: dict = translated.get(fid, {})
                    if not lang_map:
                        _cprint("WARN", job.id,
                                f"LLM returned no translations for festival_id={fid!r} — skipping")
                        continue

                    for lang, c in lang_map.items():
                        if not isinstance(c, dict) or not c:
                            continue

                        conn.execute(
                            """
                            INSERT INTO festival_content
                                (festival_id, language, name, subtitle, about,
                                 significance, history, scriptures, puja_vidhi,
                                 source_url, llm_cleaned_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                            ON CONFLICT (festival_id, language) DO UPDATE SET
                                name        = excluded.name,
                                subtitle    = excluded.subtitle,
                                about       = excluded.about,
                                significance= excluded.significance,
                                history     = excluded.history,
                                scriptures  = excluded.scriptures,
                                puja_vidhi  = excluded.puja_vidhi,
                                llm_cleaned_at = NOW()
                            """,
                            (
                                fid, lang,
                                c.get("name"), c.get("subtitle"), c.get("about"),
                                c.get("significance"), c.get("history"),
                                c.get("scriptures"), c.get("puja_vidhi"),
                                row.get("source_url"),
                            ),
                        )

                        if "rituals" in c and isinstance(c["rituals"], list):
                            conn.execute(
                                "DELETE FROM festival_rituals "
                                "WHERE festival_id=%s AND language=%s", (fid, lang),
                            )
                            with conn.cursor() as _cur:
                                _cur.executemany(
                                    "INSERT INTO festival_rituals VALUES (%s,%s,%s,%s)",
                                    [(fid, lang, pos, txt)
                                     for pos, txt in enumerate(c["rituals"])],
                                )

                        if "faqs" in c and isinstance(c["faqs"], list):
                            conn.execute(
                                "DELETE FROM festival_faqs "
                                "WHERE festival_id=%s AND language=%s", (fid, lang),
                            )
                            with conn.cursor() as _cur:
                                _cur.executemany(
                                    "INSERT INTO festival_faqs VALUES (%s,%s,%s,%s,%s)",
                                    [(fid, lang, pos, qa[0], qa[1])
                                     for pos, qa in enumerate(c["faqs"])
                                     if isinstance(qa, (list, tuple)) and len(qa) == 2],
                                )

                        written_this_batch += 1

                conn.commit()
                job.counters["written"] += written_this_batch
                _cprint("OK", job.id,
                        f"Batch {batch_num}/{total_batches} written "
                        f"({written_this_batch} language rows committed)")
            finally:
                conn.close()

    return _run


def _make_muhurat_translate_runner(req: LLMCleanRequest):
    async def _run(job: LLMJob) -> None:
        limiter = RpmLimiter(req.rpm_limit)

        conn = connect_ro()
        try:
            sql = """
                SELECT mc.muhurat_id, mc.language, mc.name, mc.description,
                       mc.vedic_basis, mc.importance, mc.source_url
                FROM muhurat_content mc
                WHERE mc.language = 'en'
            """
            params: list[Any] = []
            if not req.force:
                sql += """
                  AND NOT EXISTS (
                    SELECT 1 FROM muhurat_content mc2
                    WHERE mc2.muhurat_id = mc.muhurat_id AND mc2.language != 'en'
                  )
                """
            if req.limit:
                sql += f" LIMIT {req.limit}"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

        job.counters["fetched"] = len(rows)
        if not rows:
            _cprint("WARN", job.id,
                    "No English muhurat rows pending translation "
                    f"(force={req.force}). Run clean/muhurats first, "
                    "or pass force=true to re-translate.")
            return

        _cprint("INFO", job.id,
                f"Fetched {len(rows)} English muhurat rows → translating to "
                f"{len(TARGET_LANGUAGES)} languages "
                f"| batch_size={req.batch_size} rpm_limit={req.rpm_limit}")

        for row in rows:
            conn = connect_ro()
            try:
                row["subsections"] = [
                    [r["heading"] or "", r["body"]] for r in conn.execute(
                        "SELECT heading, body FROM muhurat_subsections "
                        "WHERE muhurat_id=%s AND language='en' AND body IS NOT NULL ORDER BY position",
                        (row["muhurat_id"],),
                    ).fetchall()
                ]
                row["faqs"] = [
                    [r["question"], r["answer"]] for r in conn.execute(
                        "SELECT question, answer FROM muhurat_faqs "
                        "WHERE muhurat_id=%s AND language='en' ORDER BY position",
                        (row["muhurat_id"],),
                    ).fetchall()
                ]
            finally:
                conn.close()

        total_batches = (len(rows) + req.batch_size - 1) // req.batch_size

        for batch_num, i in enumerate(range(0, len(rows), req.batch_size), start=1):
            batch = rows[i: i + req.batch_size]
            ids = ", ".join(r["muhurat_id"] for r in batch)
            _cprint("INFO", job.id,
                    f"Batch {batch_num}/{total_batches} "
                    f"({len(batch)} records) → translating ... "
                    f"{_DIM}[{ids}]{_RESET}")

            await limiter.acquire()
            translated = await translate_muhurat_batch(batch, model=DEFAULT_MODEL)

            if translated is None:
                job.counters["errors"] += len(batch)
                _cprint("ERROR", job.id,
                        f"Batch {batch_num}/{total_batches} FAILED (LLM error) — skipping")
                continue

            job.counters["cleaned"] += len(translated)
            _cprint("OK", job.id,
                    f"Batch {batch_num}/{total_batches} translated ({len(translated)} muhurats)")

            if req.dry_run:
                job.counters["skipped"] += len(batch)
                _cprint("WARN", job.id,
                        f"dry_run=true — batch {batch_num} NOT written to DB")
                continue

            conn = connect_rw()
            written_this_batch = 0
            try:
                for row in batch:
                    mid = row["muhurat_id"]
                    lang_map: dict = translated.get(mid, {})
                    if not lang_map:
                        _cprint("WARN", job.id,
                                f"LLM returned no translations for muhurat_id={mid!r} — skipping")
                        continue

                    for lang, c in lang_map.items():
                        if not isinstance(c, dict) or not c:
                            continue

                        conn.execute(
                            """
                            INSERT INTO muhurat_content
                                (muhurat_id, language, name, description,
                                 vedic_basis, importance, source_url, llm_cleaned_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                            ON CONFLICT (muhurat_id, language) DO UPDATE SET
                                name        = excluded.name,
                                description = excluded.description,
                                vedic_basis = excluded.vedic_basis,
                                importance  = excluded.importance,
                                llm_cleaned_at = NOW()
                            """,
                            (
                                mid, lang,
                                c.get("name"), c.get("description"),
                                c.get("vedic_basis"), c.get("importance"),
                                row.get("source_url"),
                            ),
                        )

                        if "subsections" in c and isinstance(c["subsections"], list):
                            conn.execute(
                                "DELETE FROM muhurat_subsections "
                                "WHERE muhurat_id=%s AND language=%s", (mid, lang),
                            )
                            with conn.cursor() as _cur:
                                _cur.executemany(
                                    "INSERT INTO muhurat_subsections VALUES (%s,%s,%s,%s,%s)",
                                    [(mid, lang, pos, ss[0], ss[1])
                                     for pos, ss in enumerate(c["subsections"])
                                     if isinstance(ss, (list, tuple)) and len(ss) == 2],
                                )

                        if "faqs" in c and isinstance(c["faqs"], list):
                            conn.execute(
                                "DELETE FROM muhurat_faqs "
                                "WHERE muhurat_id=%s AND language=%s", (mid, lang),
                            )
                            with conn.cursor() as _cur:
                                _cur.executemany(
                                    "INSERT INTO muhurat_faqs VALUES (%s,%s,%s,%s,%s)",
                                    [(mid, lang, pos, qa[0], qa[1])
                                     for pos, qa in enumerate(c["faqs"])
                                     if isinstance(qa, (list, tuple)) and len(qa) == 2],
                                )

                        written_this_batch += 1

                conn.commit()
                job.counters["written"] += written_this_batch
                _cprint("OK", job.id,
                        f"Batch {batch_num}/{total_batches} written "
                        f"({written_this_batch} language rows committed)")
            finally:
                conn.close()

    return _run


def _make_horoscope_translate_runner(req: LLMCleanRequest):
    async def _run(job: LLMJob) -> None:
        limiter = RpmLimiter(req.rpm_limit)

        conn = connect_ro()
        try:
            sql = """
                SELECT sign, period, language, period_key, date_label,
                       prediction, love, career, finance, health, family, advice, source_url
                FROM horoscope_predictions
                WHERE language = 'en'
                  AND (
                    prediction IS NOT NULL OR love IS NOT NULL OR
                    career IS NOT NULL OR finance IS NOT NULL OR
                    health IS NOT NULL OR family IS NOT NULL OR
                    advice IS NOT NULL
                  )
            """
            params: list[Any] = []
            if not req.force:
                sql += """
                  AND NOT EXISTS (
                    SELECT 1 FROM horoscope_predictions hp2
                    WHERE hp2.sign = horoscope_predictions.sign
                      AND hp2.period = horoscope_predictions.period
                      AND hp2.period_key = horoscope_predictions.period_key
                      AND hp2.language != 'en'
                  )
                """
            if req.limit:
                sql += f" LIMIT {req.limit}"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

        job.counters["fetched"] = len(rows)
        if not rows:
            _cprint("WARN", job.id,
                    "No English horoscope rows pending translation "
                    f"(force={req.force}). Run clean/horoscope first, "
                    "or pass force=true to re-translate.")
            return

        _cprint("INFO", job.id,
                f"Fetched {len(rows)} English horoscope rows → translating to "
                f"{len(TARGET_LANGUAGES)} languages "
                f"| batch_size={req.batch_size} rpm_limit={req.rpm_limit}")

        total_batches = (len(rows) + req.batch_size - 1) // req.batch_size

        for batch_num, i in enumerate(range(0, len(rows), req.batch_size), start=1):
            batch = rows[i: i + req.batch_size]
            ids = ", ".join(f"{r['sign']}/{r['period']}/{r['period_key']}" for r in batch)
            _cprint("INFO", job.id,
                    f"Batch {batch_num}/{total_batches} "
                    f"({len(batch)} records) → translating ... "
                    f"{_DIM}[{ids}]{_RESET}")

            await limiter.acquire()
            translated = await translate_horoscope_batch(batch, model=DEFAULT_MODEL)

            if translated is None:
                job.counters["errors"] += len(batch)
                _cprint("ERROR", job.id,
                        f"Batch {batch_num}/{total_batches} FAILED (LLM error) — skipping")
                continue

            job.counters["cleaned"] += len(translated)
            _cprint("OK", job.id,
                    f"Batch {batch_num}/{total_batches} translated ({len(translated)} horoscopes)")

            if req.dry_run:
                job.counters["skipped"] += len(batch)
                _cprint("WARN", job.id,
                        f"dry_run=true — batch {batch_num} NOT written to DB")
                continue

            conn = connect_rw()
            written_this_batch = 0
            try:
                for row in batch:
                    composite_key = f"{row['sign']}|{row['period']}|en|{row['period_key']}"
                    lang_map: dict = translated.get(composite_key, {})
                    if not lang_map:
                        _cprint("WARN", job.id,
                                f"LLM returned no translations for {composite_key!r} — skipping")
                        continue

                    for lang, c in lang_map.items():
                        if not isinstance(c, dict) or not c:
                            continue

                        conn.execute(
                            """
                            INSERT INTO horoscope_predictions
                                (sign, period, language, period_key, date_label,
                                 prediction, love, career, finance, health, family, advice,
                                 source_url, llm_cleaned_at)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                            ON CONFLICT (sign, period, language, period_key) DO UPDATE SET
                                date_label  = COALESCE(excluded.date_label, horoscope_predictions.date_label),
                                prediction  = excluded.prediction,
                                love        = excluded.love,
                                career      = excluded.career,
                                finance     = excluded.finance,
                                health      = excluded.health,
                                family      = excluded.family,
                                advice      = excluded.advice,
                                llm_cleaned_at = NOW()
                            """,
                            (
                                row["sign"], row["period"], lang, row["period_key"], row.get("date_label"),
                                c.get("prediction"), c.get("love"), c.get("career"),
                                c.get("finance"), c.get("health"), c.get("family"), c.get("advice"),
                                row.get("source_url"),
                            ),
                        )
                        written_this_batch += 1

                conn.commit()
                job.counters["written"] += written_this_batch
                _cprint("OK", job.id,
                        f"Batch {batch_num}/{total_batches} written "
                        f"({written_this_batch} language rows committed)")
            finally:
                conn.close()

    return _run


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _check_llm() -> None:
    """Raise 503 if LLM is not configured."""
    if not is_llm_enabled():
        raise HTTPException(
            503,
            "LLM is not configured. Set GROQ_API_KEY in environment "
            "and ensure LLM_SCRUB_ENABLED != 0.",
        )


@router.post("/clean/festivals")
async def clean_festivals(req: LLMCleanRequest):
    """
    Start a background LLM clean job for festival_content,
    festival_rituals, and festival_faqs.
    """
    _check_llm()
    from backend.config import LLM_MODEL
    job = LLMJobManager.start(
        category="festivals",
        model=LLM_MODEL,
        dry_run=req.dry_run,
        runner=_make_festival_runner(req),
    )
    return {"job_id": job.id, "status": job.status, **_job_summary(req)}


@router.post("/clean/muhurats")
async def clean_muhurats(req: LLMCleanRequest):
    """
    Start a background LLM clean job for muhurat_content,
    muhurat_subsections, and muhurat_faqs.
    """
    _check_llm()
    from backend.config import LLM_MODEL
    job = LLMJobManager.start(
        category="muhurats",
        model=LLM_MODEL,
        dry_run=req.dry_run,
        runner=_make_muhurat_runner(req),
    )
    return {"job_id": job.id, "status": job.status, **_job_summary(req)}


@router.post("/translate/festivals")
async def translate_festivals(req: LLMCleanRequest):
    """
    Translate cleaned English festival_content into all 11 non-English languages
    (hi, bn, ta, te, mr, gu, kn, ml, pa, sa, or) in one LLM call per batch.

    Prerequisites: run POST /clean/festivals first so English rows exist.
    Recommended batch_size: 2-3 (output is 11x larger than a clean call).
    force=true re-translates festivals that already have non-English rows.
    """
    _check_llm()
    from backend.config import LLM_MODEL
    job = LLMJobManager.start(
        category="festival-translate",
        model=LLM_MODEL,
        dry_run=req.dry_run,
        runner=_make_festival_translate_runner(req),
    )
    return {"job_id": job.id, "status": job.status, **_job_summary(req)}


@router.post("/translate/muhurats")
async def translate_muhurats(req: LLMCleanRequest):
    """
    Translate cleaned English muhurat_content into all 11 non-English languages
    in one LLM call per batch.

    Prerequisites: run POST /clean/muhurats first so English rows exist.
    Recommended batch_size: 2-3.
    force=true re-translates muhurats that already have non-English rows.
    """
    _check_llm()
    from backend.config import LLM_MODEL
    job = LLMJobManager.start(
        category="muhurat-translate",
        model=LLM_MODEL,
        dry_run=req.dry_run,
        runner=_make_muhurat_translate_runner(req),
    )
    return {"job_id": job.id, "status": job.status, **_job_summary(req)}


@router.post("/translate/horoscope")
async def translate_horoscope(req: LLMCleanRequest):
    """
    Translate cleaned English horoscope_predictions into all 11 non-English languages
    (hi, bn, ta, te, mr, gu, kn, ml, pa, sa, or) in one LLM call per batch.

    Prerequisites: run POST /clean/horoscope first so English rows exist.
    Recommended batch_size: 2-3 (output is 11x larger than a clean call).
    force=true re-translates horoscopes that already have non-English rows.
    """
    _check_llm()
    from backend.config import LLM_MODEL
    job = LLMJobManager.start(
        category="horoscope-translate",
        model=LLM_MODEL,
        dry_run=req.dry_run,
        runner=_make_horoscope_translate_runner(req),
    )
    return {"job_id": job.id, "status": job.status, **_job_summary(req)}


@router.post("/clean/horoscope")
async def clean_horoscope(req: LLMCleanRequest):
    """
    Start a background LLM clean job for horoscope_predictions.
    """
    _check_llm()
    from backend.config import LLM_MODEL
    job = LLMJobManager.start(
        category="horoscope",
        model=LLM_MODEL,
        dry_run=req.dry_run,
        runner=_make_horoscope_runner(req),
    )
    return {"job_id": job.id, "status": job.status, **_job_summary(req)}


@router.post("/clean/sign-deepdive")
async def clean_sign_deepdive(req: LLMCleanRequest):
    """
    Start a background LLM clean job for zodiac_signs (all prose columns
    including sign_intro fields and deep-dive sections from daily horoscopes).
    """
    _check_llm()
    from backend.config import LLM_MODEL
    job = LLMJobManager.start(
        category="sign-deepdive",
        model=LLM_MODEL,
        dry_run=req.dry_run,
        runner=_make_deepdive_runner(req),
    )
    return {"job_id": job.id, "status": job.status, **_job_summary(req)}


def _job_summary(req: LLMCleanRequest) -> dict:
    from backend.config import LLM_MODEL
    return {
        "model": LLM_MODEL,
        "batch_size": req.batch_size,
        "rpm_limit": req.rpm_limit,
        "language": req.language,
        "force": req.force,
        "limit": req.limit,
        "dry_run": req.dry_run,
    }


# ---------------------------------------------------------------------------
# Job management endpoints
# ---------------------------------------------------------------------------

@router.get("/jobs")
async def list_jobs(limit: int = 20):
    """List recent LLM clean jobs (in-process only — not persisted to DB)."""
    return [j.to_dict() for j in LLMJobManager.list_recent(limit)]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get live status and counters for a specific LLM clean job."""
    job = LLMJobManager.get(job_id)
    if job is None:
        raise HTTPException(404, f"Unknown job_id: {job_id!r}")
    return job.to_dict()


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running LLM clean job."""
    if not LLMJobManager.cancel(job_id):
        raise HTTPException(404, "No running job with that id.")
    return {"cancelled": True, "job_id": job_id}


@router.get("/status")
async def llm_status():
    """Check whether the LLM layer is configured and ready."""
    from backend.config import GEMINI_API_KEY, LLM_MODEL, LLM_SCRUB_ENABLED
    return {
        "enabled": is_llm_enabled(),
        "model": LLM_MODEL,
        "api_key_set": bool(GEMINI_API_KEY),
        "scrub_enabled": LLM_SCRUB_ENABLED,
    }
