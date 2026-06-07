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

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query

from backend.services.db import connect_rw, async_db
from backend.services.scraper import fetch_page, get_parser
from backend.services.scraper.registry import (
    ParsedFestival,
    ParsedMuhurat,
    classify_url,
)

router = APIRouter(prefix="/v1/admin/scrape", tags=["admin-scraper"])

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

def _start_crawl(*, scope: str, language: str, force: bool,
                 limit: int | None, resume: bool) -> dict:
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
    return job.to_dict()


@router.post("/crawl")
async def crawl(
    language: str = Query("en"),
    force: bool = Query(False, description="Re-fetch even if cached row is fresh."),
    limit: int | None = Query(None, ge=1, description="Cap pages fetched per scope."),
    resume: bool = Query(False, description="Pick up pending/failed tasks from previous runs."),
):
    """
    Kick off a background crawl. Returns immediately with a job_id;
    poll GET /v1/admin/scrape/jobs/{job_id} for progress, or POST
    .../cancel to stop it. Only one crawl runs at a time (HTTP 409 otherwise).
    """
    return _start_crawl(scope="all", language=language, force=force,
                        limit=limit, resume=resume)


@router.post("/crawl/festivals")
async def crawl_festivals_only(
    language: str = Query("en"),
    force: bool = Query(False),
    limit: int | None = Query(None, ge=1),
    resume: bool = Query(False),
):
    return _start_crawl(scope="festivals", language=language, force=force,
                        limit=limit, resume=resume)


@router.post("/crawl/muhurats")
async def crawl_muhurats_only(
    language: str = Query("en"),
    force: bool = Query(False),
    limit: int | None = Query(None, ge=1),
    resume: bool = Query(False),
):
    return _start_crawl(scope="muhurats", language=language, force=force,
                        limit=limit, resume=resume)


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
