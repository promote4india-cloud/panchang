"""
In-process crawler job manager.

Holds the currently-running asyncio.Task so the cancel endpoint can stop it,
and mirrors the lifecycle (status, started_at, finished_at) to the
`crawl_jobs` table for durable history.

Only ONE crawl runs at a time — the polite-throttle lock in fetcher.py would
serialize concurrent crawls anyway, and a single-job constraint keeps the
status/cancel UX unambiguous.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional
from uuid import uuid4

from ..db import connect_rw

log = logging.getLogger("scraper.jobs")


@dataclass
class CrawlJob:
    id: str
    scope: str               # 'all'|'festivals'|'muhurats'
    language: str
    force: bool
    is_resume: bool
    status: str = "running"  # 'running'|'completed'|'cancelled'|'failed'
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    note: Optional[str] = None
    # Live counters mutated by the orchestrator. Read by the status endpoint.
    counters: dict[str, int] = field(
        default_factory=lambda: {
            "discovered": 0, "fetched": 0, "parsed": 0,
            "persisted": 0, "skipped": 0, "errors": 0,
        }
    )
    last_url: Optional[str] = None
    # Reference to the asyncio Task so we can cancel it.
    task: Optional[asyncio.Task] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scope": self.scope,
            "language": self.language,
            "force": self.force,
            "is_resume": self.is_resume,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "note": self.note,
            "counters": dict(self.counters),
            "last_url": self.last_url,
        }


class JobManager:
    """Singleton — single crawl in flight at a time."""

    _current: Optional[CrawlJob] = None
    _lock = threading.Lock()

    @classmethod
    def current(cls) -> Optional[CrawlJob]:
        return cls._current

    @classmethod
    def start(
        cls,
        *,
        scope: str,
        language: str,
        force: bool,
        is_resume: bool,
        runner: Callable[[CrawlJob], Awaitable[None]],
    ) -> CrawlJob:
        """
        Create a CrawlJob, persist it, and schedule `runner(job)` as an
        asyncio background task. Raises if a job is already running.
        """
        with cls._lock:
            if cls._current is not None and cls._current.status == "running":
                raise RuntimeError(
                    f"A crawl is already running (job_id={cls._current.id}). "
                    "Cancel it first or wait for it to finish."
                )
            job = CrawlJob(
                id=uuid4().hex,
                scope=scope,
                language=language,
                force=force,
                is_resume=is_resume,
            )
            _persist_job(job)
            cls._current = job

        job.task = asyncio.create_task(_wrap(job, runner))
        return job

    @classmethod
    def cancel(cls) -> bool:
        """Request cancellation of the running task. Returns True if signaled."""
        job = cls._current
        if job is None or job.status != "running" or job.task is None:
            return False
        job.task.cancel()
        return True


async def _wrap(job: CrawlJob, runner: Callable[[CrawlJob], Awaitable[None]]) -> None:
    """Run the user's coroutine and pin terminal status + finished_at."""
    try:
        await runner(job)
        job.status = "completed"
    except asyncio.CancelledError:
        job.status = "cancelled"
        log.info("crawl job %s cancelled", job.id)
        # Don't re-raise — we own the lifecycle.
    except Exception as e:                       # noqa: BLE001 — terminal handler
        job.status = "failed"
        job.note = f"{type(e).__name__}: {e}"
        log.exception("crawl job %s failed", job.id)
    finally:
        job.finished_at = datetime.now(timezone.utc)
        _persist_job(job)


def _persist_job(job: CrawlJob) -> None:
    conn = connect_rw()
    try:
        conn.execute(
            """
            INSERT INTO crawl_jobs (id, scope, language, status, started_at,
                                    finished_at, is_resume, force, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                finished_at=excluded.finished_at,
                note=excluded.note
            """,
            (
                job.id, job.scope, job.language, job.status,
                job.started_at.isoformat(),
                job.finished_at.isoformat() if job.finished_at else None,
                int(job.is_resume), int(job.force), job.note,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- crawl_tasks helpers (per-URL checkpointing for resume) ----------

def upsert_task(
    *, url: str, job_id: str, scope: str, depth: int, status: str,
    error: str | None = None,
) -> None:
    conn = connect_rw()
    try:
        conn.execute(
            """
            INSERT INTO crawl_tasks (url, last_job_id, scope, depth, status,
                                     error, attempts, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 1, NOW())
            ON CONFLICT(url) DO UPDATE SET
                last_job_id=excluded.last_job_id,
                scope=excluded.scope,
                depth=excluded.depth,
                status=excluded.status,
                error=excluded.error,
                attempts=crawl_tasks.attempts + 1,
                updated_at=NOW()
            """,
            (url, job_id, scope, depth, status, error),
        )
        conn.commit()
    finally:
        conn.close()


def pending_or_failed_urls(scope: str | None = None) -> list[tuple[str, str, int]]:
    """Return [(url, scope, depth), ...] for tasks in pending/running/failed state."""
    conn = connect_rw()
    try:
        sql = (
            "SELECT url, scope, depth FROM crawl_tasks "
            "WHERE status IN ('pending','running','failed')"
        )
        params: tuple = ()
        if scope:
            sql += " AND scope = ?"
            params = (scope,)
        sql += " ORDER BY depth, url"
        return [(r["url"], r["scope"], r["depth"]) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def reset_running_to_pending() -> int:
    """On startup or before a new resume, flip any leftover 'running' to 'pending'."""
    conn = connect_rw()
    try:
        cur = conn.execute(
            "UPDATE crawl_tasks SET status='pending' WHERE status='running'"
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
