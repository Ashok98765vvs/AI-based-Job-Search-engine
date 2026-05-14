"""Reusable async rate limiter."""
from __future__ import annotations

from aiolimiter import AsyncLimiter

from config import settings

# One limiter shared across scrapers in a single event loop.
http_limiter = AsyncLimiter(max_rate=settings.http_rate_per_sec, time_period=1.0)
