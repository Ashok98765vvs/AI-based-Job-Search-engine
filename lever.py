"""Lever postings API.

Docs:
https://api.lever.co/v0/postings/{board}?mode=json
"""
from __future__ import annotations

import asyncio
from typing import Iterable, List

import httpx

from utils.http import fetch_json
from utils.logger import log

from .base import JobItem, clean_html, is_us_eligible, looks_remote, normalize, parse_dt

API = "https://api.lever.co/v0/postings/{board}?mode=json"


def _join_nonempty(parts: list[str | None]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


async def _fetch_board(client: httpx.AsyncClient, board: str) -> List[JobItem]:
    data = await fetch_json(API.format(board=board), client=client)
    if not isinstance(data, list):
        log.warning("lever[%s] invalid payload", board)
        return []

    out: List[JobItem] = []

    for j in data:
        cats = j.get("categories") or {}

        title = (j.get("text") or "").strip()
        loc = (cats.get("location") or "").strip()

        desc = _join_nonempty(
            [
                clean_html(j.get("descriptionPlain") or "", max_len=4000),
                clean_html(j.get("description") or "", max_len=4000),
                " ".join(
                    clean_html(block.get("text") or "", max_len=2000)
                    for block in (j.get("lists") or [])
                    if isinstance(block, dict)
                ),
            ]
        )[:8000]

        if not is_us_eligible(loc, title, desc):
            continue

        tags = ",".join(
            filter(
                None,
                [
                    (cats.get("team") or "").strip(),
                    (cats.get("department") or "").strip(),
                    (cats.get("commitment") or "").strip(),
                    (cats.get("allLocations") or "").strip(),
                ],
            )
        )

        out.append(
            JobItem(
                source="lever",
                external_id=str(j.get("id") or ""),
                company=board,
                title=title,
                apply_url=j.get("hostedUrl") or j.get("applyUrl") or "",
                posted_at=parse_dt(j.get("createdAt")),
                location=loc or None,
                remote=looks_remote(loc, title, desc),
                description=desc or None,
                tags=tags or None,
            )
        )

    log.info("lever[%s] %d jobs", board, len(out))
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
            log.warning("lever[%s] failed: %s", board, result)
            continue
        out.extend(result)

    return normalize(out)