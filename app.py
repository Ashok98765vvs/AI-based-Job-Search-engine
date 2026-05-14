"""USA Job Intelligence Platform — Streamlit entrypoint."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select

from ai import analyze_resume, generate_keywords, match_jobs, ollama
from components import inject_theme, render_job_card, sidebar_filters, top_metrics
from config import settings
from database import init_db, session_scope
from database.models import Job, Keyword, MatchScore, Resume
from scrapers import fetch_all_jobs, persist_jobs
from utils.exporters import to_csv, to_json, to_xlsx
from utils.logger import log
from utils.resume_parser import extract_text, save_upload

# ---------------------------------------------------------------- bootstrap

st.set_page_config(
    page_title="USA Job Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()
init_db()

if "profile" not in st.session_state:
    st.session_state.profile = None
if "resume_id" not in st.session_state:
    st.session_state.resume_id = None
if "scored_jobs" not in st.session_state:
    st.session_state.scored_jobs = []
if "last_scrape" not in st.session_state:
    st.session_state.last_scrape = None
if "extra_urls" not in st.session_state:
    st.session_state.extra_urls = ""


# ---------------------------------------------------------------- helpers


def _ollama_status_banner() -> None:
    available = ollama.is_available()
    if available:
        models = ollama.installed_models()
        ok_model = settings.ollama_model in models
        if ok_model:
            st.success(f"🟢 Ollama connected · model `{settings.ollama_model}`")
        else:
            st.warning(
                f"🟡 Ollama is running but model `{settings.ollama_model}` is not installed. "
                f"Pull it with: `ollama pull {settings.ollama_model}`"
            )
    else:
        st.warning(
            "🔴 Ollama not reachable at "
            f"`{settings.ollama_base_url}`. Resume analysis & ATS scoring will use "
            "heuristic fallbacks. Start Ollama with `ollama serve`."
        )


def _load_jobs_df() -> pd.DataFrame:
    cutoff = datetime.utcnow() - timedelta(hours=settings.fresh_window_hours)
    with session_scope() as s:
        rows = s.execute(select(Job).where(Job.posted_at >= cutoff)).scalars().all()
        data = [
            {
                "id": r.id,
                "source": r.source,
                "company": r.company,
                "title": r.title,
                "location": r.location,
                "remote": r.remote,
                "salary_min": r.salary_min,
                "salary_max": r.salary_max,
                "salary_currency": r.salary_currency or "USD",
                "description": r.description or "",
                "apply_url": r.apply_url,
                "posted_at": r.posted_at,
                "visa_sponsorship": r.visa_sponsorship,
                "tags": r.tags or "",
            }
            for r in rows
        ]
    return pd.DataFrame(data)


def _apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if f["remote_only"]:
        out = out[out["remote"] == True]  # noqa: E712
    if f["visa_only"]:
        out = out[out["visa_sponsorship"] == True]  # noqa: E712
    if f["salary_min"] > 0:
        out = out[(out["salary_max"].fillna(0) >= f["salary_min"]) | (out["salary_min"].fillna(0) >= f["salary_min"])]
    if f["companies"]:
        out = out[out["company"].isin(f["companies"])]
    if f["stack"]:
        needles = [s.lower() for s in f["stack"]]
        out = out[out["description"].str.lower().fillna("").apply(
            lambda d: all(n in d for n in needles)
        ) | out["tags"].str.lower().fillna("").apply(
            lambda d: all(n in d for n in needles)
        )]
    if f["experience"] != "Any":
        out = out[out["title"].str.lower().fillna("").str.contains(f["experience"], na=False) | (f["experience"] == "mid")]
    return out


def _persist_scores(resume_id: int, scored: list[dict]) -> None:
    with session_scope() as s:
        for j in scored:
            s.merge(MatchScore(
                resume_id=resume_id,
                job_id=int(j["id"]),
                ats_score=float(j.get("ats_score", 0)),
                semantic_score=float(j.get("semantic_score", 0)),
                keyword_match_pct=float(j.get("keyword_match_pct", 0)),
                overall=float(j.get("overall", 0)),
                explanation=j.get("explanation", ""),
            ))


def _save_resume(filename: str, raw: str, profile: dict) -> int:
    with session_scope() as s:
        r = Resume(
            filename=filename,
            raw_text=raw,
            parsed_json=json.dumps(profile),
            skills=", ".join(profile.get("tech_stack", [])),
            target_roles=", ".join(profile.get("target_roles", [])),
            years_experience=float(profile.get("years_experience") or 0),
            seniority=profile.get("seniority", "mid"),
        )
        s.add(r)
        s.flush()
        rid = r.id
        for kw in profile.get("ats_keywords", []):
            s.add(Keyword(resume_id=rid, keyword=kw, weight=1.0))
    return rid


# ---------------------------------------------------------------- UI

st.markdown(
    """
    <h1 style="margin-bottom:0;">🧠 USA Job Intelligence</h1>
    <div style="color:#9aa4c7;margin-bottom:18px;">
      Resume-aware, AI-ranked, fresh-only US job discovery — powered by Ollama.
    </div>
    """,
    unsafe_allow_html=True,
)

_ollama_status_banner()

tab_dash, tab_upload, tab_feed, tab_export, tab_admin = st.tabs(
    ["📊 Dashboard", "📄 Resume", "💼 Live Jobs", "⬇️ Export", "⚙️ Admin"]
)

# ===================== Resume tab =====================
with tab_upload:
    st.subheader("Upload your resume")
    uploaded = st.file_uploader("PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])
    if uploaded is not None:
        with st.spinner("📥 Extracting text..."):
            data = uploaded.read()
            text = extract_text(data, uploaded.name)
            save_upload(data, uploaded.name)
        st.caption(f"Extracted {len(text):,} characters.")
        with st.spinner("🤖 Asking Ollama to analyze the resume..."):
            profile = analyze_resume(text)
        rid = _save_resume(uploaded.name, text, profile)
        st.session_state.profile = profile
        st.session_state.resume_id = rid
        st.success(f"Resume analyzed and saved (id #{rid}).")

    if st.session_state.profile:
        p = st.session_state.profile
        c1, c2, c3 = st.columns(3)
        c1.metric("Seniority", p.get("seniority", "—"))
        c2.metric("Years experience", f"{p.get('years_experience', 0):.1f}")
        c3.metric("Target roles", len(p.get("target_roles", [])))

        st.markdown("##### 🎯 Target roles")
        st.write(", ".join(p.get("target_roles", [])) or "—")

        st.markdown("##### 🧰 Tech stack")
        st.write(", ".join(p.get("tech_stack", [])) or "—")

        st.markdown("##### 🔑 ATS keywords")
        st.write(", ".join(p.get("ats_keywords", [])) or "—")

        with st.expander("📝 Candidate summary"):
            st.write(p.get("summary", "—"))


# ===================== Live Jobs tab =====================
with tab_feed:
    st.subheader("Live job feed")
    st.session_state.extra_urls = st.text_area(
        "Add company career page URLs (one per line, optional)",
        value=st.session_state.extra_urls,
        height=70,
        placeholder="https://stripe.com/jobs\nhttps://boards.greenhouse.io/discord",
    )

    if st.button("🔄 Fetch fresh jobs", type="primary", use_container_width=True):
        profile = st.session_state.profile or {}
        queries = generate_keywords(
            profile.get("target_roles", []),
            profile.get("tech_stack", []),
            profile.get("seniority", "mid"),
        )
        extras = [u.strip() for u in st.session_state.extra_urls.splitlines() if u.strip()]
        with st.spinner("🌐 Scraping all sources in parallel..."):
            items = asyncio.run(fetch_all_jobs(queries, extras))
            summary = persist_jobs([i for i in items])
        st.session_state.last_scrape = summary
        st.success(
            f"Inserted {summary['inserted']} · Updated {summary['updated']} · "
            f"Pruned {summary['pruned_expired']} expired."
        )

    df = _load_jobs_df()
    filters = sidebar_filters(
        companies=df["company"].dropna().unique().tolist() if not df.empty else [],
        tech_stack=sorted({
            t.strip().lower()
            for tags in (df["tags"].dropna().tolist() if not df.empty else [])
            for t in tags.split(",")
            if t.strip()
        }),
    )
    df = _apply_filters(df, filters)

    if df.empty:
        st.info("No fresh jobs yet. Click **Fetch fresh jobs** above.")
    else:
        # Score against the current resume (in-memory only — fast).
        scored = df.to_dict(orient="records")
        if st.session_state.profile:
            with st.spinner("🧠 Scoring jobs against your resume..."):
                scored = match_jobs(st.session_state.profile, scored)
            if st.session_state.resume_id:
                _persist_scores(st.session_state.resume_id, scored)
        st.session_state.scored_jobs = scored

        # Sort
        sort_key = filters["sort_by"]
        reverse = sort_key != "posted_at"
        scored.sort(
            key=lambda j: (j.get(sort_key) is None, j.get(sort_key) or 0),
            reverse=reverse,
        )

        # Top metrics
        avg_ats = round(
            sum(j.get("ats_score", 0) for j in scored) / max(len(scored), 1), 1
        )
        top_metrics({
            "total": len(scored),
            "companies": len({j["company"] for j in scored}),
            "remote": sum(1 for j in scored if j.get("remote")),
            "avg_ats": avg_ats,
        })

        st.markdown("### Matches")
        for j in scored[:50]:
            render_job_card(j)


# ===================== Dashboard tab =====================
with tab_dash:
    st.subheader("Dashboard")
    df = _load_jobs_df()
    if df.empty:
        st.info("Fetch jobs first to see analytics.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            by_src = df.groupby("source").size().reset_index(name="count")
            fig = px.bar(by_src, x="source", y="count",
                         title="Jobs by source",
                         color="source", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            by_company = df.groupby("company").size().reset_index(name="count").sort_values("count", ascending=False).head(15)
            fig2 = px.bar(by_company, x="count", y="company", orientation="h",
                          title="Top hiring companies",
                          template="plotly_dark")
            st.plotly_chart(fig2, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            timeline = df.groupby(pd.to_datetime(df["posted_at"]).dt.floor("h")).size().reset_index(name="count")
            fig3 = px.area(timeline, x="posted_at", y="count",
                           title="Postings per hour (last 24h)", template="plotly_dark")
            st.plotly_chart(fig3, use_container_width=True)
        with c4:
            remote = df["remote"].value_counts().reset_index()
            remote.columns = ["remote", "count"]
            fig4 = px.pie(remote, names="remote", values="count",
                          title="Remote vs on-site", template="plotly_dark", hole=0.55)
            st.plotly_chart(fig4, use_container_width=True)


# ===================== Export tab =====================
with tab_export:
    st.subheader("Export")
    scored = st.session_state.scored_jobs or []
    if not scored:
        st.info("Generate matches in the **Live Jobs** tab first.")
    else:
        fmt = st.radio("Format", ["CSV", "XLSX", "JSON"], horizontal=True)
        if st.button("📦 Build export"):
            payload = [{k: v for k, v in j.items() if k != "description"} for j in scored]
            if fmt == "CSV":
                path = to_csv(payload)
                mime = "text/csv"
            elif fmt == "XLSX":
                path = to_xlsx(payload)
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                path = to_json(payload)
                mime = "application/json"
            st.success(f"Saved to `{path}`.")
            st.download_button(
                "⬇️ Download",
                data=Path(path).read_bytes(),
                file_name=path.name,
                mime=mime,
            )


# ===================== Admin tab =====================
with tab_admin:
    st.subheader("Admin")
    st.write("**Settings**")
    st.json({
        "OLLAMA_BASE_URL": settings.ollama_base_url,
        "OLLAMA_MODEL": settings.ollama_model,
        "DATABASE_URL": settings.database_url,
        "FRESH_WINDOW_HOURS": settings.fresh_window_hours,
        "GREENHOUSE_BOARDS": settings.greenhouse_list,
        "LEVER_BOARDS": settings.lever_list,
        "ASHBY_BOARDS": settings.ashby_list,
        "ADZUNA_CONFIGURED": bool(settings.adzuna_app_id and settings.adzuna_app_key),
    })
    if st.session_state.last_scrape:
        st.write("**Last scrape**")
        st.json(st.session_state.last_scrape)

    if st.button("🧹 Prune expired jobs now"):
        from scrapers.orchestrator import persist_jobs as _pj
        result = _pj([])
        st.success(f"Pruned {result['pruned_expired']} expired jobs.")

    st.caption("Tip: edit `.env` to switch model, change boards, or add Adzuna keys.")
