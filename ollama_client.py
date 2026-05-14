"""Thin wrapper around the Ollama HTTP API.

Uses POST http://localhost:11434/api/generate (default).
Falls back gracefully when Ollama isn't running so the rest of the app
keeps working in a degraded but useful mode.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import requests

from config import settings
from utils.logger import log


class OllamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout

    # ---------------------------------------------------------------- API

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def installed_models(self) -> list[str]:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            return [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            return []

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        """Single-shot completion. Returns model text or empty string on failure."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"
        try:
            r = requests.post(
                f"{self.base_url}/api/generate", json=payload, timeout=self.timeout
            )
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception as exc:
            log.warning("Ollama generate failed: %s", exc)
            return ""

    def generate_json(self, prompt: str, system: Optional[str] = None) -> dict:
        """Force structured JSON output; tolerant to fenced code blocks."""
        raw = self.generate(prompt, system=system, json_mode=True, temperature=0.1)
        if not raw:
            return {}
        return _safe_json(raw)


# ---------- helpers ----------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S | re.I)


def _safe_json(raw: str) -> dict:
    """Best-effort JSON parsing — strips markdown fences, finds the first {…}."""
    if not raw:
        return {}
    text = raw.strip()
    m = _FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except Exception:
        # try to slice the first JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {}
    return {}


# Module-level singleton for convenience.
ollama = OllamaClient()
