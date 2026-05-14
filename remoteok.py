"""RemoteOK API.

Source:
https://remoteok.com/api
"""
from __future__ import annotations

from typing import List

from utils.http import fetch_json
from utils.logger import log

from .base import JobItem, clean_html, normalize, parse_dt

API = "https://remoteok.com/api"


def _safe_float(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


async def fetch() -> List[JobItem]:
    data = await fetch_json(API)
    if not isinstance(data, list):
        log.warning("remoteok invalid payload")
        return []

    items: List[JobItem] = []

    for j in data:
        if not isinstance(j, dict):
            continue
        if not j.get("id") or not (j.get("position") or j.get("title")):
            continue

        loc = (j.get("location") or "Remote").strip()
        tags = ",".join(t.strip() for t in (j.get("tags") or []) if t and str(t).strip())

        items.append(
            JobItem(
                source="remoteok",
                external_id=str(j.get("id")),
                company=(j.get("company") or "").strip(),
                title=(j.get("position") or j.get("title") or "").strip(),
                apply_url=j.get("apply_url") or j.get("url") or "",
                posted_at=parse_dt(j.get("date") or j.get("epoch")),
                location=loc or None,
                remote=True,
                description=clean_html(j.get("description") or "", max_len=8000) or None,
                tags=tags or None,
                salary_min=_safe_float(j.get("salary_min")),
                salary_max=_safe_float(j.get("salary_max")),
            )
        )

    log.info("remoteok %d jobs", len(items))
    return normalize(items)