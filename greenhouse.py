"""Greenhouse boards scraper.

Public API:
https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
"""
from __future__ import annotations

import asyncio
from typing import Iterable, List

import httpx

from utils.http import fetch_json
from utils.logger import log

from .base import JobItem, clean_html, is_us_eligible, looks_remote, normalize, parse_dt

API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"


async def _fetch_board(client: httpx.AsyncClient, board: str) -> List[JobItem]:
    data = await fetch_json(API.format(board=board), client=client)
    if not isinstance(data, dict):
        log.warning("greenhouse[%s] invalid payload", board)
        return []

    jobs = data.get("jobs") or []
    out: List[JobItem] = []

    for j in jobs:
        title = (j.get("title") or "").strip()
        loc = ((j.get("location") or {}).get("name") or "").strip()
        desc = clean_html(j.get("content") or "", max_len=8000)

        if not is_us_eligible(loc, title, desc):
            continue

        departments = ",".join(
            d.get("name", "").strip()
            for d in (j.get("departments") or [])
            if d.get("name")
        )

        offices = ",".join(
            o.get("name", "").strip()
            for o in (j.get("offices") or [])
            if o.get("name")
        )

        tags = ",".join(filter(None, [departments, offices]))

        out.append(
            JobItem(
                source="greenhouse",
                external_id=str(j.get("id") or ""),
                company=board,
                title=title,
                apply_url=j.get("absolute_url") or "",
                posted_at=parse_dt(j.get("updated_at") or j.get("created_at")),
                location=loc or None,
                remote=looks_remote(loc, title, desc),
                description=desc,
                tags=tags or None,
            )
        )

    log.info("greenhouse[%s] %d jobs", board, len(out))
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
            log.warning("greenhouse[%s] failed: %s", board, result)
            continue
        out.extend(result)

    return normalize(out)