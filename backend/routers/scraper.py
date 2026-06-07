"""
Admin scraper endpoints (POST). Internal — should be guarded by a token /
unix-socket / VPN in production. For now they are open in dev.

  POST /v1/admin/scrape/page?url=...&language=en&force=false
        Fetches one astrosage URL (using the cached HTTP fetcher) and, if a
        parser is registered for that URL's template, parses and upserts.

  POST /v1/admin/scrape/festival/{slug_path}?language=en
        Convenience wrapper that builds the URL from the slug.

  POST /v1/admin/scrape/muhurat/{slug}?language=en
        Same for muhurats.

  GET  /v1/admin/scrape/status
        Counts of cached pages, parser errors, last fetch.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import require_admin
from backend.services.db import connect_rw, async_db
from backend.services.scraper import fetch_page, get_parser
from backend.services.scraper.registry import (
    ParsedFestival,
    ParsedMuhurat,
    classify_url,
)

router = APIRouter(
    prefix="/v1/admin/scrape",
    tags=["admin-scraper"],
    dependencies=[Depends(require_admin)],
)

ASTROSAGE_HOST = "panchang.astrosage.com"


def _ensure_host(url: str) -> list[str]:
    p = urlparse(url)
    if p.hostname != ASTROSAGE_HOST:
        raise HTTPException(400, f"Only {ASTROSAGE_HOST} URLs are accepted.")
    return [s for s in p.path.split("/") if s]


def _persist_festival(p: ParsedFestival) -> None:
    conn = connect_rw()
    try:
        # If this festival declares a parent that isn't in the DB yet, insert a
        # minimal stub so the FK holds. A later crawl of the actual parent
        # page UPSERTs full data over this stub.
        if p.parent_id:
            parent_slug = p.parent_id.replace(".", "/")
            conn.execute(
                """
                INSERT INTO festivals (id, parent_id, slug_path, kind)
                VALUES (%s, NULL, %s, 'festival')
                ON CONFLICT(id) DO NOTHING
                """,
                (p.parent_id, parent_slug),
            )
        conn.execute(
            """
            INSERT INTO festivals (id, parent_id, slug_path, kind, type,
                                   auspiciousness, rule_type, rule_json,
                                   thumbnail_url, source_url, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT(id) DO UPDATE SET
                parent_id=excluded.parent_id,
                slug_path=excluded.slug_path,
                kind=excluded.kind,
                type=excluded.type,
                auspiciousness=excluded.auspiciousness,
                rule_type=COALESCE(excluded.rule_type, festivals.rule_type),
                rule_json=COALESCE(excluded.rule_json, festivals.rule_json),
                thumbnail_url=COALESCE(excluded.thumbnail_url, festivals.thumbnail_url),
                source_url=excluded.source_url,
                updated_at=NOW()
            """,
            (p.festival_id, p.parent_id, p.slug_path, p.kind, p.type,
             p.auspiciousness, p.rule_type, p.rule_json,
             p.thumbnail_url, p.source_url),
        )
        conn.execute(
            """
            INSERT INTO festival_content (festival_id, language, name, subtitle,
                                          about, significance, history,
                                          scriptures, puja_vidhi, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(festival_id, language) DO UPDATE SET
                name=excluded.name,
                subtitle=excluded.subtitle,
                about=excluded.about,
                significance=excluded.significance,
                history=excluded.history,
                scriptures=excluded.scriptures,
                puja_vidhi=excluded.puja_vidhi,
                scraped_at=NOW(),
                source_url=excluded.source_url
            """,
            (p.festival_id, p.language, p.name, p.subtitle, p.about,
             p.significance, p.history, p.scriptures, p.puja_vidhi,
             p.source_url),
        )
        conn.execute(
            "DELETE FROM festival_rituals WHERE festival_id = %s AND language = %s",
            (p.festival_id, p.language),
        )
        with conn.cursor() as _cur:
            _cur.executemany(
                "INSERT INTO festival_rituals VALUES (%s, %s, %s, %s)",
                [(p.festival_id, p.language, i, t) for i, t in enumerate(p.rituals)],
            )
        conn.execute(
            "DELETE FROM festival_faqs WHERE festival_id = %s AND language = %s",
            (p.festival_id, p.language),
        )
        with conn.cursor() as _cur:
            _cur.executemany(
                "INSERT INTO festival_faqs VALUES (%s, %s, %s, %s, %s)",
                [(p.festival_id, p.language, i, q, a) for i, (q, a) in enumerate(p.faqs)],
            )
        conn.commit()
    finally:
        conn.close()


def _persist_muhurat(p: ParsedMuhurat) -> None:
    conn = connect_rw()
    try:
        conn.execute(
            """
            INSERT INTO muhurat_types (id, category, computable, source_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                category=excluded.category,
                computable=excluded.computable,
                source_url=excluded.source_url
            """,
            (p.muhurat_id, p.category, int(p.computable), p.source_url),
        )
        conn.execute(
            """
            INSERT INTO muhurat_content (muhurat_id, language, name, description,
                                         vedic_basis, importance, source_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(muhurat_id, language) DO UPDATE SET
                name=excluded.name,
                description=excluded.description,
                vedic_basis=excluded.vedic_basis,
                importance=excluded.importance,
                scraped_at=NOW(),
                source_url=excluded.source_url
            """,
            (p.muhurat_id, p.language, p.name, p.description,
             p.vedic_basis, p.importance, p.source_url),
        )
        conn.execute(
            "DELETE FROM muhurat_subsections WHERE muhurat_id = %s AND language = %s",
            (p.muhurat_id, p.language),
        )
        with conn.cursor() as _cur:
            _cur.executemany(
                "INSERT INTO muhurat_subsections VALUES (%s, %s, %s, %s, %s)",
                [(p.muhurat_id, p.language, i, h, b)
                 for i, (h, b) in enumerate(p.subsections)],
            )
        conn.execute(
            "DELETE FROM muhurat_faqs WHERE muhurat_id = %s AND language = %s",
            (p.muhurat_id, p.language),
        )
        with conn.cursor() as _cur:
            _cur.executemany(
                "INSERT INTO muhurat_faqs VALUES (%s, %s, %s, %s, %s)",
                [(p.muhurat_id, p.language, i, q, a) for i, (q, a) in enumerate(p.faqs)],
            )
        conn.commit()
    finally:
        conn.close()


@router.post("/page")
async def scrape_page(
    url: str = Query(..., description="Full astrosage URL"),
    language: str = Query("en"),
    force: bool = Query(False),
):
    parts = _ensure_host(url)
    try:
        kind = classify_url(parts)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Importing parsers package triggers @register_parser side-effects.
    # Done lazily so a missing parser only fails the parse step, not import.
    from backend.services.scraper import parsers as _parsers  # noqa: F401

    html = await fetch_page(url, scope=("festival" if "festival" in kind else "muhurat"),
                            ref_id=None, language=language, force=force)
    try:
        parser = get_parser(kind)
    except KeyError as e:
        return {
            "url": url, "template_kind": kind, "fetched": True, "parsed": False,
            "detail": str(e),
        }
    parsed = parser(html, url)
    if isinstance(parsed, ParsedFestival):
        _persist_festival(parsed)
        return {"url": url, "template_kind": kind, "parsed": "festival", "id": parsed.festival_id}
    if isinstance(parsed, ParsedMuhurat):
        _persist_muhurat(parsed)
        return {"url": url, "template_kind": kind, "parsed": "muhurat", "id": parsed.muhurat_id}
    raise HTTPException(500, f"Parser returned unexpected type: {type(parsed)}")


@router.post("/festival/{slug_path:path}")
async def scrape_festival(slug_path: str, language: str = "en", force: bool = False):
    url = f"https://{ASTROSAGE_HOST}/festival/{slug_path}?language={language}"
    return await scrape_page(url=url, language=language, force=force)


@router.post("/muhurat/{slug}")
async def scrape_muhurat(slug: str, language: str = "en", force: bool = False):
    url = f"https://{ASTROSAGE_HOST}/muhurat/{slug}?language={language}"
    return await scrape_page(url=url, language=language, force=force)


# -------------------------------------------------------------------------
# Background crawl: start / poll status / cancel / resume.
# Only ONE crawl runs at a time (enforced by JobManager).
# -------------------------------------------------------------------------

async def _chain_after_crawl(
    crawl_job,
    scope: str,
    auto_clean: bool,
    auto_translate: bool,
) -> None:
    """
    Background task: waits for the crawl to finish, then runs LLM clean and/or
    translate phases sequentially (to keep rate-limit pressure predictable).
    Only proceeds if the crawl completed successfully.
    """
    if crawl_job.task is not None:
        try:
            await crawl_job.task
        except (asyncio.CancelledError, Exception):
            pass

    if crawl_job.status != "completed":
        print(
            f"[chain] crawl {crawl_job.id[:8]} ended with "
            f"status={crawl_job.status!r} — skipping LLM chain",
            flush=True,
        )
        return

    print(
        f"[chain] crawl {crawl_job.id[:8]} done — "
        f"starting pipeline (clean={auto_clean} translate={auto_translate})",
        flush=True,
    )

    # Lazy imports to avoid circular dependency at module load time.
    from backend.routers.llm import (
        LLMJobManager,
        LLMCleanRequest,
        _make_festival_runner,
        _make_muhurat_runner,
        _make_festival_translate_runner,
        _make_muhurat_translate_runner,
    )
    from backend.services.llm import DEFAULT_MODEL, is_llm_enabled

    if not is_llm_enabled():
        print("[chain] LLM not configured — skipping clean/translate phases", flush=True)
        return

    clean_req = LLMCleanRequest()                    # batch_size=10 is fine for cleaning
    translate_req = LLMCleanRequest(batch_size=3)    # 11 languages × 10 festivals = huge output

    if auto_clean:
        print("[chain] Phase 1/2: LLM clean", flush=True)
        if scope in ("all", "festivals"):
            fj = LLMJobManager.start(
                category="festivals", model=DEFAULT_MODEL, dry_run=False,
                runner=_make_festival_runner(clean_req),
            )
            if fj.task:
                await asyncio.shield(fj.task)
            print(f"[chain] festivals clean done (status={fj.status})", flush=True)

        if scope in ("all", "muhurats"):
            mj = LLMJobManager.start(
                category="muhurats", model=DEFAULT_MODEL, dry_run=False,
                runner=_make_muhurat_runner(clean_req),
            )
            if mj.task:
                await asyncio.shield(mj.task)
            print(f"[chain] muhurats clean done (status={mj.status})", flush=True)

    if auto_translate:
        print("[chain] Phase 2/2: LLM translate", flush=True)
        if scope in ("all", "festivals"):
            ftj = LLMJobManager.start(
                category="festival-translate", model=DEFAULT_MODEL, dry_run=False,
                runner=_make_festival_translate_runner(translate_req),
            )
            if ftj.task:
                await asyncio.shield(ftj.task)
            print(f"[chain] festivals translate done (status={ftj.status})", flush=True)

        if scope in ("all", "muhurats"):
            mtj = LLMJobManager.start(
                category="muhurat-translate", model=DEFAULT_MODEL, dry_run=False,
                runner=_make_muhurat_translate_runner(translate_req),
            )
            if mtj.task:
                await asyncio.shield(mtj.task)
            print(f"[chain] muhurats translate done (status={mtj.status})", flush=True)

    print(f"[chain] pipeline complete for crawl {crawl_job.id[:8]}", flush=True)


def _start_crawl(
    *,
    scope: str,
    language: str,
    force: bool,
    limit: int | None,
    resume: bool,
    auto_clean: bool = False,
    auto_translate: bool = False,
) -> dict:
    # Trigger parser registration before the orchestrator runs.
    from backend.services.scraper import parsers as _parsers  # noqa: F401
    from backend.services.scraper.jobs import JobManager
    from backend.services.scraper.orchestrator import make_runner
    runner = make_runner(scope=scope, force=force, limit=limit, resume=resume)
    try:
        job = JobManager.start(
            scope=scope, language=language, force=force, is_resume=resume,
            runner=runner,
        )
    except RuntimeError as e:
        raise HTTPException(409, str(e))

    if auto_clean or auto_translate:
        asyncio.create_task(_chain_after_crawl(job, scope, auto_clean, auto_translate))

    out = job.to_dict()
    if auto_clean or auto_translate:
        out["auto_chain"] = {"clean": auto_clean, "translate": auto_translate}
    return out


@router.post("/crawl")
async def crawl(
    language: str = Query("en"),
    force: bool = Query(False, description="Re-fetch even if cached row is fresh."),
    limit: int | None = Query(None, ge=1, description="Cap pages fetched per scope."),
    resume: bool = Query(False, description="Pick up pending/failed tasks from previous runs."),
    auto_clean: bool = Query(True, description="Auto-run LLM clean after crawl completes."),
    auto_translate: bool = Query(True, description="Auto-run LLM translate after clean completes."),
):
    """
    Kick off a background crawl. Returns immediately with a job_id;
    poll GET /v1/admin/scrape/jobs/{job_id} for progress, or POST
    .../cancel to stop it. Only one crawl runs at a time (HTTP 409 otherwise).

    auto_clean and auto_translate both default to true — the full pipeline
    (crawl → LLM clean → translate into 11 languages) runs automatically.
    Pass auto_clean=false to crawl only; auto_translate=false to crawl + clean only.
    """
    return _start_crawl(scope="all", language=language, force=force,
                        limit=limit, resume=resume,
                        auto_clean=auto_clean or auto_translate,
                        auto_translate=auto_translate)


@router.post("/crawl/festivals")
async def crawl_festivals_only(
    language: str = Query("en"),
    force: bool = Query(False),
    limit: int | None = Query(None, ge=1),
    resume: bool = Query(False),
    auto_clean: bool = Query(True, description="Auto-run LLM clean after crawl completes."),
    auto_translate: bool = Query(True, description="Auto-run LLM translate after clean completes."),
):
    return _start_crawl(scope="festivals", language=language, force=force,
                        limit=limit, resume=resume,
                        auto_clean=auto_clean or auto_translate,
                        auto_translate=auto_translate)


@router.post("/crawl/muhurats")
async def crawl_muhurats_only(
    language: str = Query("en"),
    force: bool = Query(False),
    limit: int | None = Query(None, ge=1),
    resume: bool = Query(False),
    auto_clean: bool = Query(True, description="Auto-run LLM clean after crawl completes."),
    auto_translate: bool = Query(True, description="Auto-run LLM translate after clean completes."),
):
    return _start_crawl(scope="muhurats", language=language, force=force,
                        limit=limit, resume=resume,
                        auto_clean=auto_clean or auto_translate,
                        auto_translate=auto_translate)


# -------------------------------------------------------------------------
# Horoscope pre-warm: bulk-fetch all signs × periods, then auto-clean.
# -------------------------------------------------------------------------

_VALID_PERIODS = frozenset({
    "daily", "tomorrow", "weekly", "weekly_love",
    "monthly", "next_month", "yearly",
})


async def _run_horoscope_prewarm(
    *,
    periods: list[str],
    language: str,
    force: bool,
    auto_clean: bool,
    auto_translate: bool,
    auto_deepdive: bool,
) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from backend.services.horoscope import SIGNS, get_horoscope

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    total = len(SIGNS) * len(periods)
    fetched = 0
    errors = 0

    print(
        f"[horoscope-prewarm] Starting — "
        f"{len(SIGNS)} signs × {len(periods)} periods = {total} pages",
        flush=True,
    )

    for sign in SIGNS:
        for period in periods:
            try:
                await get_horoscope(
                    sign=sign, period=period, d=today,
                    language=language, tz="Asia/Kolkata", force=force,
                )
                fetched += 1
            except Exception as exc:  # noqa: BLE001
                errors += 1
                print(
                    f"[horoscope-prewarm] {sign}/{period} FAILED: {exc}",
                    flush=True,
                )

    print(
        f"[horoscope-prewarm] Fetch done — fetched={fetched} errors={errors}",
        flush=True,
    )

    if not (auto_clean or auto_translate or auto_deepdive):
        return

    from backend.routers.llm import (
        LLMJobManager,
        LLMCleanRequest,
        _make_horoscope_runner,
        _make_deepdive_runner,
        _make_horoscope_translate_runner,
    )
    from backend.services.llm import DEFAULT_MODEL, is_llm_enabled

    if not is_llm_enabled():
        print(
            "[horoscope-prewarm] LLM not configured — skipping clean phases",
            flush=True,
        )
        return

    req = LLMCleanRequest()

    if auto_clean:
        print("[horoscope-prewarm] Starting LLM clean/horoscope ...", flush=True)
        hj = LLMJobManager.start(
            category="horoscope", model=DEFAULT_MODEL, dry_run=False,
            runner=_make_horoscope_runner(req),
        )
        if hj.task:
            await asyncio.shield(hj.task)
        print(
            f"[horoscope-prewarm] horoscope clean done (status={hj.status})",
            flush=True,
        )

    if auto_translate:
        print("[horoscope-prewarm] Starting LLM translate/horoscope ...", flush=True)
        tj = LLMJobManager.start(
            category="horoscope-translate", model=DEFAULT_MODEL, dry_run=False,
            runner=_make_horoscope_translate_runner(req),
        )
        if tj.task:
            await asyncio.shield(tj.task)
        print(
            f"[horoscope-prewarm] horoscope translate done (status={tj.status})",
            flush=True,
        )

    if auto_deepdive:
        print("[horoscope-prewarm] Starting LLM clean/sign-deepdive ...", flush=True)
        dj = LLMJobManager.start(
            category="sign-deepdive", model=DEFAULT_MODEL, dry_run=False,
            runner=_make_deepdive_runner(req),
        )
        if dj.task:
            await asyncio.shield(dj.task)
        print(
            f"[horoscope-prewarm] sign-deepdive clean done (status={dj.status})",
            flush=True,
        )

    print("[horoscope-prewarm] Pipeline complete.", flush=True)


@router.post("/horoscope")
async def prewarm_horoscope(
    periods: str = Query(
        "daily,weekly,monthly",
        description=(
            "Comma-separated periods to pre-fetch. "
            "Valid values: daily, tomorrow, weekly, weekly_love, monthly, next_month, yearly."
        ),
    ),
    language: str = Query("en"),
    force: bool = Query(False, description="Re-fetch even if already cached."),
    auto_clean: bool = Query(
        True,
        description="Run LLM clean/horoscope after all pages are fetched.",
    ),
    auto_translate: bool = Query(
        True,
        description="Run LLM translate/horoscope after horoscope clean.",
    ),
    auto_deepdive: bool = Query(
        False,
        description="Run LLM clean/sign-deepdive after horoscope clean/translate. Implies auto_clean.",
    ),
):
    """
    Pre-warm horoscope predictions for all 12 signs and the given periods.
    Runs in the background; returns immediately with a summary.
    Track LLM clean/translation progress via GET /v1/admin/llm/jobs.
    """
    period_list = [p.strip() for p in periods.split(",") if p.strip()]
    invalid = [p for p in period_list if p not in _VALID_PERIODS]
    if invalid:
        raise HTTPException(
            400,
            f"Unknown periods: {invalid}. Valid: {sorted(_VALID_PERIODS)}",
        )

    asyncio.create_task(
        _run_horoscope_prewarm(
            periods=period_list,
            language=language,
            force=force,
            auto_clean=auto_clean or auto_deepdive or auto_translate,
            auto_translate=auto_translate,
            auto_deepdive=auto_deepdive,
        )
    )

    from backend.services.horoscope import SIGNS
    return {
        "status": "started",
        "signs": list(SIGNS),
        "periods": period_list,
        "language": language,
        "total_pages": len(SIGNS) * len(period_list),
        "auto_clean": auto_clean or auto_deepdive or auto_translate,
        "auto_translate": auto_translate,
        "auto_deepdive": auto_deepdive,
    }


@router.post("/horoscope/cleanup")
async def cleanup_horoscope_cache(
    tz: str = Query(
        "Asia/Kolkata",
        description="Timezone used to determine the current calendar window.",
    ),
):
    """
    Delete stale horoscope_predictions rows from the DB.

    A row is stale when its period_key is before the current calendar window
    for that period type (e.g., a daily row from yesterday, a weekly row from
    last week). Returns the count of deleted rows and the cutoff keys used.
    """
    from backend.services.horoscope import cleanup_stale_horoscopes

    result = await asyncio.to_thread(cleanup_stale_horoscopes, tz)
    return result


@router.post("/jobs/current/cancel")
async def cancel_current_job():
    """Cancel the currently-running crawl. Idempotent (404 if no job)."""
    from backend.services.scraper.jobs import JobManager
    if not JobManager.cancel():
        raise HTTPException(404, "No crawl is currently running.")
    job = JobManager.current()
    return {"cancelled": True, "job_id": job.id if job else None}


@router.get("/jobs/current")
async def current_job():
    from backend.services.scraper.jobs import JobManager
    job = JobManager.current()
    if job is None:
        return {"status": "idle"}
    return job.to_dict()


@router.get("/jobs")
async def list_jobs(limit: int = Query(20, ge=1, le=200)):
    async with async_db() as conn:
        cur = await conn.execute(
            "SELECT * FROM crawl_jobs ORDER BY started_at DESC LIMIT %s", (limit,),
        )
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str):
    from backend.services.scraper.jobs import JobManager
    live = JobManager.current()
    async with async_db() as conn:
        cur = await conn.execute(
            "SELECT * FROM crawl_jobs WHERE id = %s", (job_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, f"Unknown job_id: {job_id}")
        cur = await conn.execute(
            "SELECT status, COUNT(*) n FROM crawl_tasks "
            "WHERE last_job_id = %s GROUP BY status",
            (job_id,),
        )
        task_counts = {
            r["status"]: r["n"]
            for r in await cur.fetchall()
        }
        cur = await conn.execute(
            "SELECT url, error, updated_at FROM crawl_tasks "
            "WHERE last_job_id = %s AND status = 'failed' "
            "ORDER BY updated_at DESC LIMIT 25",
            (job_id,),
        )
        recent_errors = [dict(r) for r in await cur.fetchall()]
    out = dict(row)
    out["task_counts"] = task_counts
    out["recent_errors"] = recent_errors
    if live and live.id == job_id:
        out["live"] = live.to_dict()
    return out


@router.get("/tasks")
async def list_tasks(
    status: str | None = Query(None, description="pending|running|done|failed|cancelled"),
    scope: str | None = Query(None, description="festival|muhurat"),
    limit: int = Query(100, ge=1, le=1000),
):
    sql = "SELECT * FROM crawl_tasks WHERE 1=1"
    params: list = []
    if status:
        sql += " AND status = %s"; params.append(status)
    if scope:
        sql += " AND scope = %s";  params.append(scope)
    sql += " ORDER BY updated_at DESC LIMIT %s"
    params.append(limit)
    async with async_db() as conn:
        cur = await conn.execute(sql, params)
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/status")
async def status():
    async with async_db() as conn:
        cur = await conn.execute("SELECT COUNT(*) c FROM scraped_pages")
        scraped = (await cur.fetchone())["c"]
        cur = await conn.execute("SELECT COUNT(*) c FROM festivals")
        festivals_count = (await cur.fetchone())["c"]
        cur = await conn.execute("SELECT COUNT(*) c FROM festival_content")
        fc_count = (await cur.fetchone())["c"]
        cur = await conn.execute("SELECT COUNT(*) c FROM muhurat_types")
        mt_count = (await cur.fetchone())["c"]
        cur = await conn.execute("SELECT COUNT(*) c FROM muhurat_content")
        mc_count = (await cur.fetchone())["c"]
        counts = {
            "scraped_pages": scraped,
            "festivals": festivals_count,
            "festival_content": fc_count,
            "muhurat_types": mt_count,
            "muhurat_content": mc_count,
        }
        cur = await conn.execute(
            "SELECT url, parse_error FROM scraped_pages WHERE parse_error IS NOT NULL LIMIT 25"
        )
        errors = await cur.fetchall()
        cur = await conn.execute(
            "SELECT url, fetched_at FROM scraped_pages ORDER BY fetched_at DESC LIMIT 5"
        )
        last = await cur.fetchall()
    return {
        "counts": counts,
        "recent_errors": [dict(r) for r in errors],
        "recent_fetches": [dict(r) for r in last],
    }
