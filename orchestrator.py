"""Orchestrate every job source in parallel and persist fresh jobs."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from sqlalchemy import select

from config import settings
from database import session_scope
from database.models import Job
from utils.logger import log

from . import adzuna, arbeitnow, ashby, company_page, greenhouse, lever, remoteok, remotive
from .base import JobItem, normalize

_SOURCES = [
    ("greenhouse",  lambda kw: greenhouse.fetch(settings.greenhouse_list)),
    ("lever",       lambda kw: lever.fetch(settings.lever_list)),
    ("ashby",       lambda kw: ashby.fetch(settings.ashby_list)),
    ("remotive",    lambda kw: remotive.fetch(kw)),
    ("remoteok",    lambda kw: remoteok.fetch()),
    ("arbeitnow",   lambda kw: arbeitnow.fetch()),
    ("adzuna",      lambda kw: adzuna.fetch(kw, pages=2, max_days_old=3)),
]


async def fetch_all_jobs(
    keywords: Optional[Iterable[str]] = None,
    extra_company_urls: Optional[Iterable[str]] = None,
) -> List[JobItem]:
    """Run every scraper concurrently. Returns deduplicated items."""
    kw = list(keywords) if keywords else None
    extra = [u.strip() for u in (extra_company_urls or []) if u and u.strip()]

    log.info(
        "Starting parallel scrape — %d sources, %d keywords, %d extra URLs",
        len(_SOURCES), len(kw or []), len(extra),
    )

    # Build task list with source names for labeling errors
    named_tasks: list[tuple[str, asyncio.Task]] = []
    async with asyncio.TaskGroup() if False else _nullctx():
        pass  # placeholder — use gather below

    coroutines = [(name, fn(kw)) for name, fn in _SOURCES]
    for url in extra:
        coroutines.append((f"company_page:{url}", company_page.scrape(url)))

    results = await asyncio.gather(*[coro for _, coro in coroutines], return_exceptions=True)

    all_items: List[JobItem] = []
    for (name, _), result in zip(coroutines, results):
        if isinstance(result, Exception):
            log.warning("source[%s] error: %s", name, result)
            continue
        if isinstance(result, list):
            log.debug("source[%s] returned %d items", name, len(result))
            all_items.extend(result)

    log.info("Total fetched (pre-dedup): %d", len(all_items))
    deduped = normalize(all_items)
    log.info("Total after dedup: %d", len(deduped))
    return deduped


# ─── Persistence ─────────────────────────────────────────────────────────────

def _is_fresh(dt: datetime, hours: int) -> bool:
    if not dt:
        return False
    return (datetime.utcnow() - dt) <= timedelta(hours=hours)


def persist_jobs(items: List[JobItem], fresh_hours: Optional[int] = None) -> dict:
    """Insert or update fresh items, prune stale ones. Returns a summary dict."""
    fresh_hours = fresh_hours if fresh_hours is not None else settings.fresh_window_hours
    inserted = updated = skipped_stale = 0

    with session_scope() as s:
        cutoff = datetime.utcnow() - timedelta(hours=fresh_hours)
        expired = s.query(Job).filter(Job.posted_at < cutoff).delete()
        log.info("Pruned %d expired jobs (older than %dh)", expired, fresh_hours)

        for it in items:
            if not _is_fresh(it.posted_at, fresh_hours):
                skipped_stale += 1
                continue

            existing = s.execute(
                select(Job).where(
                    Job.source == it.source,
                    Job.external_id == it.external_id,
                )
            ).scalar_one_or_none()

            if existing:
                existing.title = it.title
                existing.company = it.company
                existing.location = it.location
                existing.remote = it.remote
                existing.salary_min = it.salary_min
                existing.salary_max = it.salary_max
                existing.description = it.description
                existing.apply_url = it.apply_url
                existing.posted_at = it.posted_at
                existing.fetched_at = datetime.utcnow()
                existing.tags = it.tags
                updated += 1
            else:
                s.add(Job(**it.to_dict()))
                inserted += 1

    summary = {
        "fetched": len(items),
        "inserted": inserted,
        "updated": updated,
        "skipped_stale": skipped_stale,
        "pruned_expired": expired,
    }
    log.info("Persist summary: %s", summary)
    return summary


class _nullctx:
    async def __aenter__(self): return self
    async def __aexit__(self, *_): pass