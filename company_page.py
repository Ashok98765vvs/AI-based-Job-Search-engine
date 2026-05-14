"""Generic company careers-page scraper.

Strategy:
1. Detect common hosted ATS boards from the URL and route to the structured scraper.
2. Otherwise fetch the HTML and extract links that look like job postings.
3. Use broad title/location/URL hints so generic company sites still return useful jobs.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from utils.http import fetch_text
from utils.logger import log

from . import ashby, greenhouse, lever
from .base import JobItem, clean_html, looks_remote, normalize, normalize_url

_JOB_HINT = re.compile(
    r"(/jobs?/|/job/|/careers?/|/positions?/|/openings?/|/vacancies?/|gh_jid=|jobId=|job_id=)",
    re.I,
)

_TITLE_HINT = re.compile(
    r"(engineer|developer|designer|manager|analyst|scientist|architect|consultant|intern|lead|director|"
    r"software|frontend|front[- ]end|backend|back[- ]end|full[- ]stack|full stack|devops|qa|sre|data|ml|ai|python)",
    re.I,
)

_BAD_TEXT = re.compile(
    r"^(apply|read more|learn more|view all|see all|careers|jobs|open roles|open positions)$",
    re.I,
)


def _extract_slug(url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not parts:
        return ""
    return parts[-1]


def _company_from_host(host: str) -> str:
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 2:
        return parts[-2]
    return host


async def _route_known_boards(url: str) -> List[JobItem] | None:
    host = urlparse(url).netloc.lower()
    slug = _extract_slug(url)

    if "greenhouse.io" in host or "boards.greenhouse.io" in host:
        return await greenhouse.fetch([slug])

    if "lever.co" in host or "jobs.lever.co" in host:
        return await lever.fetch([slug])

    if "ashbyhq.com" in host:
        return await ashby.fetch([slug])

    return None


def _collect_meta_description(soup: BeautifulSoup) -> str:
    bits: list[str] = []

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if title:
        bits.append(title)

    for attrs in (
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            bits.append(tag["content"])

    return clean_html(" ".join(bits), max_len=1000)


async def scrape(url: str) -> List[JobItem]:
    """Scrape a company careers page or hosted board URL."""
    routed = await _route_known_boards(url)
    if routed is not None:
        return routed

    html = await fetch_text(url)
    if not html:
        log.warning("company_page[%s] empty html", url)
        return []

    soup = BeautifulSoup(html, "lxml")
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    company = _company_from_host(host)
    page_context = _collect_meta_description(soup)

    items: List[JobItem] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        text = " ".join(a.get_text(" ", strip=True).split())

        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue

        if not text or len(text) < 4:
            continue

        if _BAD_TEXT.match(text):
            continue

        full = normalize_url(urljoin(url, href))
        if not full or full in seen:
            continue

        combined = f"{text} {href}"

        if not (_JOB_HINT.search(href) or _TITLE_HINT.search(text) or _TITLE_HINT.search(combined)):
            continue

        seen.add(full)

        items.append(
            JobItem(
                source="company_page",
                external_id=full,
                company=company,
                title=text[:200],
                apply_url=full,
                posted_at=datetime.utcnow(),
                location=None,
                remote=looks_remote(text, href, page_context),
                description=page_context or None,
                tags=None,
            )
        )

    log.info("company_page[%s] %d jobs", host, len(items))
    return normalize(items)