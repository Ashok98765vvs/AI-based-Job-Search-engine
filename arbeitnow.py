"""Arbeitnow jobs API.

Source:
https://arbeitnow.com/api/job-board-api
"""
from __future__ import annotations

from typing import List

from utils.http import fetch_json
from utils.logger import log

from .base import JobItem, clean_html, is_us_eligible, looks_remote, normalize, parse_dt

API = "https://arbeitnow.com/api/job-board-api"


async def fetch() -> List[JobItem]:
    data = await fetch_json(API)
    if not isinstance(data, dict):
        log.warning("arbeitnow invalid payload")
        return []

    items: List[JobItem] = []

    for j in data.get("data", []):
        title = (j.get("title") or "").strip()
        company = (j.get("company_name") or "").strip()
        loc = (j.get("location") or "").strip()
        desc = clean_html(j.get("description") or "", max_len=8000)

        if not is_us_eligible(loc, title, desc):
            continue

        tags = ",".join(t.strip() for t in (j.get("tags") or []) if t and str(t).strip())

        items.append(
            JobItem(
                source="arbeitnow",
                external_id=str(j.get("slug") or j.get("id") or ""),
                company=company,
                title=title,
                apply_url=j.get("url") or "",
                posted_at=parse_dt(j.get("created_at")),
                location=loc or None,
                remote=bool(j.get("remote")) or looks_remote(loc, title, desc),
                description=desc or None,
                tags=tags or None,
            )
        )

    log.info("arbeitnow %d jobs", len(items))
    return normalize(items)