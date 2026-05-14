"""ATS / semantic matching engine."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from utils.logger import log

from .ollama_client import OllamaClient, ollama

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]{1,}")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def keyword_match_pct(resume_keywords: Iterable[str], job_text: str) -> float:
    """Return percentage of resume keywords present in the job description."""
    kws = [k.lower().strip() for k in resume_keywords if k and k.strip()]
    if not kws:
        return 0.0
    text = (job_text or "").lower()
    hits = sum(1 for k in kws if k in text)
    return round(100.0 * hits / len(kws), 2)


@dataclass
class ATSResult:
    ats_score: float
    semantic_score: float
    keyword_match_pct: float
    overall: float
    explanation: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


_SYSTEM = (
    "You are an ATS scoring engine. Evaluate how well a candidate's resume profile "
    "matches a single job description. Return STRICT JSON only."
)

_PROMPT = """Score the match. Return JSON:

{{
  "ats_score": 0-100,            // ATS keyword + structure compatibility
  "semantic_score": 0-100,       // role/responsibility semantic fit
  "explanation": string          // 2 short sentences, candidate-friendly
}}

CANDIDATE PROFILE:
- Target roles: {roles}
- Seniority: {seniority}
- Years experience: {years}
- Tech stack: {stack}
- ATS keywords: {ats_keywords}

JOB:
Title: {job_title}
Company: {company}
Location: {location} | Remote: {remote}
Description:
\"\"\"{description}\"\"\"
"""


def ats_score(
    profile: dict,
    job: dict,
    client: Optional[OllamaClient] = None,
) -> ATSResult:
    """Compute ATS + semantic + keyword scores for a single job."""
    client = client or ollama
    job_text = " ".join(
        str(job.get(f, "") or "") for f in ("title", "company", "location", "description", "tags")
    )
    kw_pct = keyword_match_pct(
        list(profile.get("ats_keywords", [])) + list(profile.get("tech_stack", [])),
        job_text,
    )

    ats, sem, expl = kw_pct, kw_pct, ""
    if client.is_available():
        data = client.generate_json(
            _PROMPT.format(
                roles=", ".join(profile.get("target_roles", [])) or "—",
                seniority=profile.get("seniority", "mid"),
                years=profile.get("years_experience", 0),
                stack=", ".join(profile.get("tech_stack", [])) or "—",
                ats_keywords=", ".join(profile.get("ats_keywords", [])) or "—",
                job_title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location", "") or "—",
                remote="yes" if job.get("remote") else "no",
                description=(job.get("description") or "")[:4000],
            ),
            system=_SYSTEM,
        )
        try:
            ats = float(data.get("ats_score", kw_pct))
            sem = float(data.get("semantic_score", kw_pct))
            expl = str(data.get("explanation", "") or "")
        except Exception as e:
            log.warning("ATS parse failed: %s — falling back to keyword score.", e)

    ats = max(0.0, min(100.0, ats))
    sem = max(0.0, min(100.0, sem))
    overall = round(0.45 * ats + 0.45 * sem + 0.10 * kw_pct, 2)

    return ATSResult(
        ats_score=round(ats, 2),
        semantic_score=round(sem, 2),
        keyword_match_pct=kw_pct,
        overall=overall,
        explanation=expl or _fallback_explanation(kw_pct),
    )


def _fallback_explanation(pct: float) -> str:
    if pct >= 75:
        return "Strong keyword overlap — likely a great fit. Tailor your summary to mirror the JD."
    if pct >= 45:
        return "Decent overlap. Highlight the matching skills near the top of the resume."
    return "Limited overlap. Consider adding missing keywords or pursuing more aligned roles."


def match_jobs(profile: dict, jobs: List[dict], client: Optional[OllamaClient] = None) -> List[dict]:
    """Score & sort jobs against the profile."""
    out: List[dict] = []
    for job in jobs:
        res = ats_score(profile, job, client=client)
        merged = {**job, **res.as_dict()}
        out.append(merged)
    out.sort(key=lambda j: j.get("overall", 0), reverse=True)
    return out
