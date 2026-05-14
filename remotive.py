"""Remotive API.

Source:
https://remotive.com/api/remote-jobs
"""
from __future__ import annotations

from typing import Iterable, List, Optional

from utils.http import fetch_json
from utils.logger import log

from .base import JobItem, clean_html, is_us_eligible, looks_remote, normalize, parse_dt

API = "https://remotive.com/api/remote-jobs"


async def fetch(queries: Optional[Iterable[str]] = None, limit: int = 100) -> List[JobItem]:
    queries = [q.strip() for q in (queries or [""]) if q is not None]
    if not queries:
        queries = [""]

    all_items: List[JobItem] = []

    for q in queries:
        params = {"limit": limit}
        if q:
            params["search"] = q

        data = await fetch_json(API, params=params)
        if not isinstance(data, dict):
            log.warning("remotive invalid payload for query=%r", q)
            continue

        for j in data.get("jobs", []):
            title = (j.get("title") or "").strip()
            company = (j.get("company_name") or "").strip()
            loc = (j.get("candidate_required_location") or "Remote").strip()
            desc = clean_html(j.get("description") or "", max_len=8000)

            if not is_us_eligible(loc, title, desc):
                continue

            tags = ",".join(t.strip() for t in (j.get("tags") or []) if t and str(t).strip())

            all_items.append(
                JobItem(
                    source="remotive",
                    external_id=str(j.get("id") or ""),
                    company=company,
                    title=title,
                    apply_url=j.get("url") or "",
                    posted_at=parse_dt(j.get("publication_date")),
                    location=loc or None,
                    remote=True or looks_remote(loc, title, desc),
                    description=desc or None,
                    tags=tags or None,
                    salary_min=None,
                    salary_max=None,
                )
            )

    log.info("remotive %d jobs", len(all_items))
    return normalize(all_items)