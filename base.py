"""Base utilities + canonical job item dataclass."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

_ISO_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
)

_US_HINTS = (
    "united states",
    "usa",
    "u.s.",
    "us only",
    "u.s. only",
    "remote us",
    "remote - us",
    "remote, us",
    "us remote",
    "north america",
)

_STATE_HINTS = (
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
    "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
    "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
    "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
)

_CITY_HINTS = (
    "new york", "san francisco", "seattle", "austin", "boston",
    "chicago", "los angeles", "denver", "atlanta", "miami",
    "dallas", "houston", "phoenix", "washington", "remote",
)

_REMOTE_HINTS = (
    "remote", "work from home", "distributed", "anywhere", "worldwide",
    "hybrid remote", "remote-first", "remote friendly",
)


def parse_dt(value: Any) -> datetime:
    """Best-effort timestamp parser -> naive UTC datetime."""
    if value is None:
        return datetime.utcnow()

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    else:
        s = str(value).strip()
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            dt = None

        if dt is None:
            for fmt in _ISO_FORMATS:
                try:
                    dt = datetime.strptime(s, fmt)
                    break
                except Exception:
                    continue

        if dt is None:
            return datetime.utcnow()

    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def clean_html(value: str | None, max_len: int = 8000) -> str:
    """Convert HTML to readable plain text."""
    if not value:
        return ""
    try:
        text = BeautifulSoup(value, "lxml").get_text(" ", strip=True)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", value)
        text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def normalize_url(url: str | None) -> str:
    """Normalize URLs for stable dedupe."""
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
        return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))
    except Exception:
        return (url or "").strip()


def looks_remote(*parts: str | None) -> bool:
    blob = " ".join([p for p in parts if p]).lower()
    return any(hint in blob for hint in _REMOTE_HINTS)


def is_us_eligible(location: str | None, title: str | None = None, description: str | None = None) -> bool:
    """Loose filter for US or remote-friendly roles."""
    blob = " ".join([location or "", title or "", description or ""]).lower()

    if not blob.strip():
        return True

    if any(h in blob for h in _US_HINTS):
        return True

    if any(h in blob for h in _CITY_HINTS):
        return True

    if any(h in blob for h in _REMOTE_HINTS):
        return True

    tokens = set(re.findall(r"\b[a-z]{2}\b", blob))
    if any(state in tokens for state in _STATE_HINTS):
        return True

    return False


@dataclass
class JobItem:
    source: str
    external_id: str
    company: str
    title: str
    apply_url: str
    posted_at: datetime
    location: Optional[str] = None
    remote: bool = False
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "USD"
    description: Optional[str] = None
    visa_sponsorship: Optional[bool] = None
    tags: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["apply_url"] = normalize_url(d.get("apply_url"))
        return d


def _dedupe_key(item: JobItem) -> tuple[str, str, str]:
    url = normalize_url(item.apply_url)
    if url:
        return (item.company.strip().lower(), item.title.strip().lower(), url)
    return (item.source.strip().lower(), str(item.external_id).strip().lower(), item.title.strip().lower())


def normalize(items: list[JobItem]) -> list[JobItem]:
    """Deduplicate within a single scrape run."""
    seen: set[tuple[str, str, str]] = set()
    out: list[JobItem] = []

    for it in items:
        it.apply_url = normalize_url(it.apply_url)
        it.company = (it.company or "").strip()
        it.title = re.sub(r"\s+", " ", (it.title or "").strip())
        it.location = re.sub(r"\s+", " ", (it.location or "").strip()) or None
        it.description = clean_html(it.description, max_len=8000) if it.description else None
        it.remote = bool(it.remote or looks_remote(it.location, it.title, it.description))

        key = _dedupe_key(it)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)

    return out