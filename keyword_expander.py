"""Expand target roles into related search queries."""
from __future__ import annotations

from typing import Iterable, List, Optional

from .ollama_client import OllamaClient, ollama

_SYSTEM = "You are an expert tech recruiter. Reply with JSON only."

_PROMPT = """Given the candidate roles and tech stack, generate up to 15 closely related
US job titles to search for. Be specific. Return JSON:

{{ "queries": [string, ...] }}

ROLES: {roles}
STACK: {stack}
SENIORITY: {seniority}
"""


def generate_keywords(
    target_roles: Iterable[str],
    tech_stack: Iterable[str],
    seniority: str = "mid",
    client: Optional[OllamaClient] = None,
) -> List[str]:
    client = client or ollama
    roles = ", ".join(target_roles) or "Software Engineer"
    stack = ", ".join(tech_stack) or "python"

    if client.is_available():
        data = client.generate_json(
            _PROMPT.format(roles=roles, stack=stack, seniority=seniority),
            system=_SYSTEM,
        )
        queries = data.get("queries") or []
        out = [str(q).strip() for q in queries if str(q).strip()]
        if out:
            return _dedupe(out)

    # Fallback: simple synonyms
    base = list(target_roles) or ["Software Engineer"]
    suffixes = ["", "Engineer", "Developer", "Specialist", "Lead"]
    prefixes = ["", "Senior", "Lead", "Staff"] if seniority in ("senior", "staff") else [""]
    out = [f"{p} {b} {s}".strip() for b in base for p in prefixes for s in suffixes]
    return _dedupe(out)


def _dedupe(items: Iterable[str]) -> List[str]:
    seen, out = set(), []
    for it in items:
        k = " ".join(it.split()).lower()
        if k and k not in seen:
            seen.add(k)
            out.append(" ".join(it.split()))
    return out
