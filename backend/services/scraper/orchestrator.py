"""
Async crawl orchestrator — fetch + parse + persist the entire astrosage
festival / muhurat catalog.

Designed for MANUAL invocation. Key properties:

  * Async (httpx.AsyncClient via fetcher.fetch_page) so the FastAPI worker
    stays responsive during a multi-minute crawl.
  * Polite — 1 req/s throttle is enforced in the fetcher; we share one
    AsyncClient per crawl scope to reuse connections.
  * Cancellable — the loop awaits at every fetch, so an asyncio.Task.cancel()
    interrupts cleanly. Any URL caught mid-flight is left as 'pending' in
    `crawl_tasks`, ready for resume.
  * Resumable — every URL we touch is upserted into `crawl_tasks` with its
    status. `resume=True` re-loads pending/failed rows instead of
    re-discovering from the index.

Counters on the CrawlJob are mutated live so the status endpoint can stream
progress without waiting for completion.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from urllib.parse import urlparse

import httpx

from .fetcher import DEFAULT_HEADERS, DEFAULT_MAX_AGE, fetch_page
from .jobs import (
    CrawlJob,
    pending_or_failed_urls,
    reset_running_to_pending,
    upsert_task,
)
from .parsers import _html_utils as h
from .registry import ParsedFestival, ParsedMuhurat, classify_url, get_parser

log = logging.getLogger("scraper.orchestrator")

ASTROSAGE_HOST = "panchang.astrosage.com"
ROOT_FESTIVAL = f"https://{ASTROSAGE_HOST}/festival"
ROOT_MUHURAT = f"https://{ASTROSAGE_HOST}/muhurat"

MAX_FESTIVAL_DEPTH = 3  # /festival/<a>/<b>/<c>

# Slugs confirmed by the site map to have no page at /festival/<slug2>.
# They only serve as parent containers for depth-3 URLs.
_FESTIVAL_NO_L2_PAGE: frozenset[str] = frozenset({
    "baisakhi", "cheti-chand", "dussehra", "ganesh-chaturthi",
    "gudi-padwa", "guru-purnima", "hanuman-jayanti", "holi",
    "janmashtami", "karvachauth", "nag-panchami", "onam",
    "shivratri", "teej", "ugadi",
})

# (slug2, slug3) pairs with no page at /festival/<slug2>/<slug3>.
# They only serve as parent containers for depth-4 URLs.
_FESTIVAL_NO_L3_PAGE: frozenset[tuple[str, str]] = frozenset({
    ("diwali", "dhanteras"),
    ("diwali", "govardhanpuja"),
    ("diwali", "narak-chaturdashi"),
    ("navratri", "chaitra-navratri"),
    ("navratri", "durga-puja"),
    ("navratri", "sharad-navratri"),
})


# --- discovery helpers -----------------------------------------------------

def _path_parts(url: str) -> list[str]:
    return [p for p in urlparse(url).path.split("/") if p]


def _extract_festival_index(html_text: str) -> list[str]:
    soup = h.soup_of(html_text)
    return h.extract_internal_links(soup, ROOT_FESTIVAL, "/festival/")


def _extract_muhurat_index(html_text: str) -> list[str]:
    soup = h.soup_of(html_text)
    return h.extract_internal_links(soup, ROOT_MUHURAT, "/muhurat/")


def _ancestors(urls: list[str]) -> list[str]:
    """For each /a/b/c URL, also queue /a/b and /a (shallow first).

    Skips intermediate paths that are known container-only nodes with no
    real page on astrosage (confirmed via site map analysis).
    """
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        parts = _path_parts(u)
        for i in range(2, len(parts) + 1):
            seg = parts[:i]
            if seg[0] == "festival":
                if len(seg) == 2 and seg[1] in _FESTIVAL_NO_L2_PAGE:
                    continue
                if len(seg) == 3 and (seg[1], seg[2]) in _FESTIVAL_NO_L3_PAGE:
                    continue
            ancestor = f"https://{ASTROSAGE_HOST}/" + "/".join(seg)
            if ancestor not in seen:
                seen.add(ancestor)
                out.append(ancestor)
    out.sort(key=lambda u: len(_path_parts(u)))
    return out


def _persist(parsed, /) -> None:
    """Delegate to the canonical UPSERT helpers in routers/scraper.py."""
    from routers.scraper import _persist_festival, _persist_muhurat
    if isinstance(parsed, ParsedFestival):
        _persist_festival(parsed)
    elif isinstance(parsed, ParsedMuhurat):
        _persist_muhurat(parsed)
    else:
        raise TypeError(f"Unknown parsed type: {type(parsed)!r}")


# --- core per-URL worker ---------------------------------------------------

async def _process_url(
    *,
    job: CrawlJob,
    url: str,
    scope: str,
    depth: int,
    force: bool,
    max_age: timedelta,
    client: httpx.AsyncClient,
) -> ParsedFestival | ParsedMuhurat | None:
    """
    Fetch, parse, persist a single URL. Updates job counters + crawl_tasks
    state. Returns the parsed object (so the festival loop can BFS children),
    or None on skip / failure.
    """
    parts = _path_parts(url)

    # Listing pages have no per-record parser — short-circuit.
    if scope == "festival" and len(parts) >= 2 and parts[1] == "today-festival":
        job.counters["skipped"] += 1
        upsert_task(url=url, job_id=job.id, scope=scope, depth=depth, status="done")
        return None
    if scope == "festival" and (depth == 0 or depth > MAX_FESTIVAL_DEPTH):
        job.counters["skipped"] += 1
        upsert_task(url=url, job_id=job.id, scope=scope, depth=depth, status="done")
        return None

    job.last_url = url
    upsert_task(url=url, job_id=job.id, scope=scope, depth=depth, status="running")

    try:
        kind = classify_url(parts) if scope == "festival" else "muhurat_detail"
    except ValueError as e:
        job.counters["errors"] += 1
        upsert_task(url=url, job_id=job.id, scope=scope, depth=depth,
                    status="failed", error=str(e))
        return None

    try:
        html_text = await fetch_page(
            url, scope=scope, ref_id=parts[-1] if parts else None,
            language=job.language, force=force, max_age=max_age, client=client,
        )
        job.counters["fetched"] += 1
    except Exception as e:                                # noqa: BLE001
        job.counters["errors"] += 1
        upsert_task(url=url, job_id=job.id, scope=scope, depth=depth,
                    status="failed", error=f"fetch: {e}")
        return None

    try:
        parsed = get_parser(kind)(html_text, url)
        job.counters["parsed"] += 1
    except Exception as e:                                # noqa: BLE001
        job.counters["errors"] += 1
        upsert_task(url=url, job_id=job.id, scope=scope, depth=depth,
                    status="failed", error=f"parse({kind}): {e}")
        return None

    try:
        # DB write is sync but small. Offload to a thread so the event loop
        # stays free for other requests.
        await asyncio.to_thread(_persist, parsed)
        job.counters["persisted"] += 1
    except Exception as e:                                # noqa: BLE001
        job.counters["errors"] += 1
        upsert_task(url=url, job_id=job.id, scope=scope, depth=depth,
                    status="failed", error=f"persist: {e}")
        return None

    upsert_task(url=url, job_id=job.id, scope=scope, depth=depth, status="done")
    return parsed


# --- scope-level entry points ---------------------------------------------

async def crawl_festivals(
    job: CrawlJob,
    *,
    force: bool = False,
    max_age: timedelta = DEFAULT_MAX_AGE,
    limit: int | None = None,
    resume: bool = False,
) -> None:
    """BFS the /festival tree. Mutates `job.counters` live."""
    headers = {**DEFAULT_HEADERS, "Accept-Language": job.language}
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=30.0, headers=headers,
    ) as client:
        if resume:
            queue: list[tuple[str, int]] = [
                (url, depth) for url, _scope, depth in pending_or_failed_urls("festival")
            ]
        else:
            try:
                index_html = await fetch_page(
                    ROOT_FESTIVAL, scope="festival_list", ref_id=None,
                    language=job.language, force=force, max_age=max_age,
                    client=client,
                )
                job.counters["fetched"] += 1
            except Exception as e:                                # noqa: BLE001
                job.note = f"festival index fetch failed: {e}"
                return
            raw = _extract_festival_index(index_html)
            urls = _ancestors(raw)
            queue = [(u, len(_path_parts(u)) - 1) for u in urls]

        seen: set[str] = {u for u, _ in queue}
        # Mark all as pending up front so /jobs/{id} progress is accurate
        # even before each URL is processed.
        for u, d in queue:
            upsert_task(url=u, job_id=job.id, scope="festival",
                        depth=d, status="pending")
        job.counters["discovered"] += len(queue)

        processed = 0
        while queue:
            if limit is not None and processed >= limit:
                break
            url, depth = queue.pop(0)
            parsed = await _process_url(
                job=job, url=url, scope="festival", depth=depth,
                force=force, max_age=max_age, client=client,
            )
            processed += 1

            # BFS-expand children declared on a festival_top page.
            if isinstance(parsed, ParsedFestival):
                for sub_slug in parsed.child_slugs:
                    sub_parts = sub_slug.split("/")
                    if len(sub_parts) > MAX_FESTIVAL_DEPTH:
                        continue
                    if len(sub_parts) == 1 and sub_parts[0] in _FESTIVAL_NO_L2_PAGE:
                        continue
                    if len(sub_parts) == 2 and (sub_parts[0], sub_parts[1]) in _FESTIVAL_NO_L3_PAGE:
                        continue
                    child_url = f"https://{ASTROSAGE_HOST}/festival/{sub_slug}"
                    if child_url not in seen:
                        seen.add(child_url)
                        child_depth = len(_path_parts(child_url)) - 1
                        queue.append((child_url, child_depth))
                        upsert_task(
                            url=child_url, job_id=job.id, scope="festival",
                            depth=child_depth, status="pending",
                        )
                        job.counters["discovered"] += 1


async def crawl_muhurats(
    job: CrawlJob,
    *,
    force: bool = False,
    max_age: timedelta = DEFAULT_MAX_AGE,
    limit: int | None = None,
    resume: bool = False,
) -> None:
    headers = {**DEFAULT_HEADERS, "Accept-Language": job.language}
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=30.0, headers=headers,
    ) as client:
        if resume:
            queue: list[tuple[str, int]] = [
                (url, depth) for url, _scope, depth in pending_or_failed_urls("muhurat")
            ]
        else:
            try:
                index_html = await fetch_page(
                    ROOT_MUHURAT, scope="muhurat_list", ref_id=None,
                    language=job.language, force=force, max_age=max_age,
                    client=client,
                )
                job.counters["fetched"] += 1
            except Exception as e:                                # noqa: BLE001
                job.note = f"muhurat index fetch failed: {e}"
                return
            urls = _extract_muhurat_index(index_html)
            queue = [(u, len(_path_parts(u)) - 1) for u in urls]

        for u, d in queue:
            upsert_task(url=u, job_id=job.id, scope="muhurat",
                        depth=d, status="pending")
        job.counters["discovered"] += len(queue)

        processed = 0
        for url, depth in queue:
            if limit is not None and processed >= limit:
                break
            await _process_url(
                job=job, url=url, scope="muhurat", depth=depth,
                force=force, max_age=max_age, client=client,
            )
            processed += 1


# --- runner factory --------------------------------------------------------

def make_runner(
    *,
    scope: str,                 # 'all'|'festivals'|'muhurats'
    force: bool,
    limit: int | None,
    resume: bool,
):
    """Build the coroutine the JobManager schedules on the event loop."""
    if resume:
        reset_running_to_pending()  # heal any interrupted run

    async def _run(job: CrawlJob) -> None:
        if scope in ("all", "festivals"):
            await crawl_festivals(job, force=force, limit=limit, resume=resume)
        if scope in ("all", "muhurats"):
            await crawl_muhurats(job, force=force, limit=limit, resume=resume)

    return _run
