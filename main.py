"""FastAPI app exposing the same services as the Streamlit UI.

Run:
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from ai import analyze_resume, generate_keywords, match_jobs
from config import settings
from database import init_db, session_scope
from database.models import Job
from scrapers import fetch_all_jobs, persist_jobs
from utils.resume_parser import extract_text

app = FastAPI(title="USA Job Intelligence API", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()


class JobOut(BaseModel):
    id: int
    source: str
    company: str
    title: str
    location: Optional[str]
    remote: bool
    salary_min: Optional[float]
    salary_max: Optional[float]
    apply_url: str
    posted_at: datetime
    tags: Optional[str]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/jobs", response_model=List[JobOut])
def list_jobs(limit: int = 100) -> List[JobOut]:
    cutoff = datetime.utcnow() - timedelta(hours=settings.fresh_window_hours)
    with session_scope() as s:
        rows = (
            s.execute(select(Job).where(Job.posted_at >= cutoff).limit(limit))
            .scalars()
            .all()
        )
        return [JobOut(**{c.name: getattr(r, c.name) for c in Job.__table__.columns
                         if c.name in JobOut.model_fields}) for r in rows]


@app.post("/scrape")
async def scrape(keywords: Optional[List[str]] = None,
                 extra_urls: Optional[List[str]] = None) -> dict:
    items = await fetch_all_jobs(keywords, extra_urls)
    summary = persist_jobs(items)
    return summary


@app.post("/analyze-resume")
async def analyze(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    try:
        text = extract_text(data, file.filename or "resume")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    profile = analyze_resume(text)
    queries = generate_keywords(
        profile.get("target_roles", []),
        profile.get("tech_stack", []),
        profile.get("seniority", "mid"),
    )
    return {"profile": profile, "suggested_queries": queries}


@app.post("/match")
async def match(profile: dict) -> List[dict]:
    cutoff = datetime.utcnow() - timedelta(hours=settings.fresh_window_hours)
    with session_scope() as s:
        rows = s.execute(select(Job).where(Job.posted_at >= cutoff)).scalars().all()
        jobs = [
            {c.name: getattr(r, c.name) for c in Job.__table__.columns} for r in rows
        ]
    return match_jobs(profile, jobs)
