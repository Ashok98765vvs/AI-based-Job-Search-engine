"""Adzuna jobs API.

Docs:
https://developer.adzuna.com/
"""
from __future__ import annotations

from typing import Iterable, List, Optional

from config import settings
from utils.http import fetch_json
from utils.logger import log

from .base import JobItem, clean_html, is_us_eligible, looks_remote, normalize, parse_dt

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


async def fetch(
    queries: Optional[Iterable[str]] = None,
    pages: int = 2,
    max_days_old: int = 3,
) -> List[JobItem]:
    if not (settings.adzuna_app_id and settings.adzuna_app_key):
        log.info("Adzuna keys not set — skipping.")
        return []

    queries = [q.strip() for q in (queries or ["software engineer"]) if q and q.strip()]
    if not queries:
        queries = ["software engineer"]

    items: List[JobItem] = []

    for q in queries:
        for page in range(1, pages + 1):
            params = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "results_per_page": settings.adzuna_results_per_page,
                "what": q,
                "max_days_old": max_days_old,
                "content-type": "application/json",
            }

            url = API.format(country=settings.adzuna_country, page=page)
            data = await fetch_json(url, params=params)

            if not isinstance(data, dict):
                log.warning("adzuna invalid payload for query=%r page=%s", q, page)
                continue

            for j in data.get("results", []):
                title = (j.get("title") or "").strip()
                company = ((j.get("company") or {}).get("display_name") or "").strip()
                loc = ((j.get("location") or {}).get("display_name") or "").strip()
                desc = clean_html(j.get("description") or "", max_len=8000)

                if not is_us_eligible(loc, title, desc):
                    continue

                cat = ((j.get("category") or {}).get("label") or "").strip()

                items.append(
                    JobItem(
                        source="adzuna",
                        external_id=str(j.get("id") or ""),
                        company=company,
                        title=title,
                        apply_url=j.get("redirect_url") or "",
                        posted_at=parse_dt(j.get("created")),
                        location=loc or None,
                        remote=looks_remote(loc, title, desc),
                        salary_min=j.get("salary_min"),
                        salary_max=j.get("salary_max"),
                        description=desc or None,
                        tags=cat or None,
                    )
                )

    log.info("adzuna %d jobs", len(items))
    return normalize(items)