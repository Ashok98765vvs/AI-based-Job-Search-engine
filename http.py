"""Shared async HTTP client with retries, rate limiting and rotating UAs."""
from __future__ import annotations

from typing import Any, Optional

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from utils.logger import log
from utils.rate_limiter import http_limiter
from utils.user_agents import random_user_agent

_RETRYABLE = (httpx.TransportError, httpx.HTTPStatusError, httpx.ReadTimeout)


async def fetch_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[Any]:
    """GET a JSON endpoint with retries + rate limiting. Returns None on failure."""
    headers = {"User-Agent": random_user_agent(), **(headers or {})}
    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=settings.http_timeout)

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.http_retries),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception_type(_RETRYABLE),
            reraise=False,
        ):
            with attempt:
                async with http_limiter:
                    r = await client.get(url, params=params, headers=headers)
                    r.raise_for_status()
                    try:
                        return r.json()
                    except Exception:
                        log.warning("Non-JSON response from %s", url)
                        return None
    except Exception as exc:
        log.warning("fetch_json failed for %s: %s", url, exc)
        return None
    finally:
        if own:
            await client.aclose()


async def fetch_text(
    url: str,
    headers: Optional[dict] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[str]:
    """GET raw text/HTML with retries."""
    headers = {"User-Agent": random_user_agent(), **(headers or {})}
    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=settings.http_timeout, follow_redirects=True)

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.http_retries),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
            retry=retry_if_exception_type(_RETRYABLE),
            reraise=False,
        ):
            with attempt:
                async with http_limiter:
                    r = await client.get(url, headers=headers)
                    r.raise_for_status()
                    return r.text
    except Exception as exc:
        log.warning("fetch_text failed for %s: %s", url, exc)
        return None
    finally:
        if own:
            await client.aclose()
