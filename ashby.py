"""Ashby public job board API.

Endpoint:
https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true
"""
from __future__ import annotations

import asyncio
import re
from typing import Iterable, List, Optional, Tuple

import httpx

from utils.http import fetch_json
from utils.logger import log

from .base import JobItem, clean_html, is_us_eligible, looks_remote, normalize, parse_dt

API = "https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true"


def _parse_salary(compensation: dict) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    currency = compensation.get("currencyCode") or compensation.get("currency") or "USD"

    for min_key, max_key in (
        ("minCompensation", "maxCompensation"),
        ("minSalary", "maxSalary"),
        ("salaryMin", "salaryMax"),
    ):
        min_val = compensation.get(min_key)
        max_val = compensation.get(max_key)
        if isinstance(min_val, (int, float)) or isinstance(max_val, (int, float)):
            return (
                float(min_val) if min_val is not None else None,
                float(max_val) if max_val is not None else None,
                currency,
            )

    summary = compensation.get("compensationTierSummary") or compensation.get("summary") or ""
    if not summary:
        return None, None, currency

    text = str(summary)
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*([Kk]?)", text)
    if len(nums) >= 2:
        def cvt(pair: tuple[str, str]) -> float:
            num, suffix = pair
            value = float(num)
            return value * 1000 if suffix.lower() == "k" else value

        return cvt(nums[0]), cvt(nums[1]), currency

    if len(nums) == 1:
        value = float(nums[0][0]) * (1000 if nums[0][1].lower() == "k" else 1)
        return value, value, currency

    return None, None, currency


async def _fetch_board(client: httpx.AsyncClient, board: str) -> List[JobItem]:
    data = await fetch_json(API.format(board=board), client=client)
    if not isinstance(data, dict):
        log.warning("ashby[%s] invalid payload", board)
        return []

    jobs = data.get("jobs") or []
    out: List[JobItem] = []

    for j in jobs:
        title = (j.get("title") or "").strip()
        loc = (j.get("location") or "").strip()
        desc = clean_html(j.get("descriptionHtml") or "", max_len=8000)

        if not is_us_eligible(loc, title, desc):
            continue

        comp = j.get("compensation") or {}
        salary_min, salary_max, salary_currency = _parse_salary(comp)

        tags = ",".join(
            filter(
                None,
                [
                    (j.get("department") or "").strip(),
                    (j.get("team") or "").strip(),
                    (j.get("employmentType") or "").strip(),
                ],
            )
        )

        out.append(
            JobItem(
                source="ashby",
                external_id=str(j.get("id") or ""),
                company=board,
                title=title,
                apply_url=j.get("jobUrl") or j.get("applyUrl") or "",
                posted_at=parse_dt(j.get("publishedAt") or j.get("updatedAt")),
                location=loc or None,
                remote=bool(j.get("isRemote")) or looks_remote(loc, title, desc),
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=salary_currency,
                description=desc or None,
                tags=tags or None,
            )
        )

    log.info("ashby[%s] %d jobs", board, len(out))
    return out


async def fetch(boards: Iterable[str]) -> List[JobItem]:
    boards = [b.strip() for b in boards if b and b.strip()]
    if not boards:
        return []

    async with httpx.AsyncClient(timeout=30) as client:
        results = await asyncio.gather(
            *[_fetch_board(client, board) for board in boards],
            return_exceptions=True,
        )

    out: List[JobItem] = []
    for board, result in zip(boards, results):
        if isinstance(result, Exception):
            log.warning("ashby[%s] failed: %s", board, result)
            continue
        out.extend(result)

    return normalize(out)