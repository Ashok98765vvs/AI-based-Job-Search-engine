"""Resume → structured profile using Ollama."""
from __future__ import annotations

from typing import Optional

from utils.logger import log
from utils.resume_parser import quick_fields

from .ollama_client import OllamaClient, ollama

_SYSTEM = (
    "You are a senior US tech recruiter and ATS expert. "
    "Extract a clean structured profile from the candidate resume. "
    "Respond with STRICT JSON ONLY, no commentary."
)

_PROMPT = """Analyze the resume below and return JSON with this exact shape:

{{
  "target_roles": [string],          // primary role titles the candidate fits
  "related_roles": [string],         // adjacent/lateral roles to also search
  "seniority": "junior|mid|senior|staff|principal|executive",
  "years_experience": number,        // best estimate (0 if new grad)
  "tech_stack": [string],            // tools, languages, frameworks
  "soft_skills": [string],
  "certifications": [string],
  "education": [string],
  "industries": [string],
  "ats_keywords": [string],          // hidden/likely keywords ATS will look for
  "summary": string                  // 2-sentence candidate summary
}}

RESUME:
\"\"\"
{resume_text}
\"\"\"
"""


def analyze_resume(text: str, client: Optional[OllamaClient] = None) -> dict:
    """Return a structured profile dict. Falls back to heuristics if Ollama is down."""
    client = client or ollama
    profile: dict = {}
    if client.is_available():
        profile = client.generate_json(_PROMPT.format(resume_text=text[:12000]), system=_SYSTEM)
        if not profile:
            log.warning("Ollama returned empty profile — using heuristics.")

    if not profile:
        guess = quick_fields(text)
        profile = {
            "target_roles": [],
            "related_roles": [],
            "seniority": "mid",
            "years_experience": guess.get("years_experience_guess") or 0,
            "tech_stack": guess.get("skills_guess", []),
            "soft_skills": [],
            "certifications": [],
            "education": [],
            "industries": [],
            "ats_keywords": guess.get("skills_guess", []),
            "summary": "Heuristic profile (Ollama unavailable).",
        }

    # Normalize
    for k in (
        "target_roles", "related_roles", "tech_stack", "soft_skills",
        "certifications", "education", "industries", "ats_keywords",
    ):
        profile[k] = [str(x).strip() for x in (profile.get(k) or []) if str(x).strip()]
    try:
        profile["years_experience"] = float(profile.get("years_experience") or 0)
    except Exception:
        profile["years_experience"] = 0.0
    profile["seniority"] = str(profile.get("seniority") or "mid").lower()
    profile["summary"] = str(profile.get("summary") or "")

    return profile
