"""Rotating user-agent helper."""
from __future__ import annotations

import random
from typing import List

_FALLBACK_UAS: List[str] = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
]

try:
    from fake_useragent import UserAgent  # type: ignore

    _ua = UserAgent(fallback=_FALLBACK_UAS[0])

    def random_user_agent() -> str:
        try:
            return _ua.random
        except Exception:
            return random.choice(_FALLBACK_UAS)

except Exception:  # library may fail offline
    def random_user_agent() -> str:  # type: ignore[misc]
        return random.choice(_FALLBACK_UAS)
