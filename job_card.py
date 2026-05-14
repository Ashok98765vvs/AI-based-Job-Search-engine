"""Single job card renderer."""
from __future__ import annotations

import html
from datetime import datetime

import streamlit as st


def _fmt_salary(j: dict) -> str:
    lo, hi = j.get("salary_min"), j.get("salary_max")
    cur = j.get("salary_currency") or "USD"
    if lo and hi:
        return f"${int(lo):,} – ${int(hi):,} {cur}"
    if lo:
        return f"From ${int(lo):,} {cur}"
    if hi:
        return f"Up to ${int(hi):,} {cur}"
    return "Salary not disclosed"


def _fmt_age(dt) -> str:
    if not dt:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    delta = datetime.utcnow() - dt
    hours = int(delta.total_seconds() // 3600)
    if hours < 1:
        return "just now"
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def _badges(j: dict) -> str:
    out = []
    if j.get("remote"):
        out.append('<span class="badge success">Remote</span>')
    if j.get("visa_sponsorship"):
        out.append('<span class="badge info">Visa Sponsor</span>')
    if j.get("source"):
        out.append(f'<span class="badge">{html.escape(str(j["source"]))}</span>')
    if j.get("tags"):
        for t in str(j["tags"]).split(",")[:5]:
            t = t.strip()
            if t:
                out.append(f'<span class="badge warn">{html.escape(t)}</span>')
    return " ".join(out)


def render_job_card(j: dict) -> None:
    overall = float(j.get("overall") or 0)
    ats = float(j.get("ats_score") or 0)
    sem = float(j.get("semantic_score") or 0)
    kw = float(j.get("keyword_match_pct") or 0)

    title = html.escape(str(j.get("title", "Untitled")))
    company = html.escape(str(j.get("company", "—")))
    location = html.escape(str(j.get("location") or "—"))
    expl = html.escape(str(j.get("explanation") or ""))
    apply_url = j.get("apply_url") or "#"

    st.markdown(
        f"""
        <div class="job-card">
            <div style="display:flex; gap:18px; align-items:flex-start; justify-content:space-between;">
              <div style="flex:1;">
                <div class="title">{title}</div>
                <div class="meta">{company} · {location} · {_fmt_age(j.get('posted_at'))} · {_fmt_salary(j)}</div>
                <div class="badges">{_badges(j)}</div>
                <div style="margin-top:10px; color: var(--muted); font-size: 13px;">{expl}</div>
                <div class="apply-link"><a href="{apply_url}" target="_blank">Apply →</a></div>
              </div>
              <div style="display:flex; flex-direction:column; align-items:center; gap:6px;">
                <div class="score-ring" style="--p:{overall:.0f};">{overall:.0f}</div>
                <div style="font-size:11px;color:var(--muted);">ATS {ats:.0f} · SEM {sem:.0f} · KW {kw:.0f}%</div>
              </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
