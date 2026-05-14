"""Dashboard metrics row."""
from __future__ import annotations

import streamlit as st


def metric(label: str, value: str) -> str:
    return f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
    </div>
    """


def top_metrics(stats: dict) -> None:
    cols = st.columns(4)
    items = [
        ("Total fresh jobs", stats.get("total", 0)),
        ("Companies", stats.get("companies", 0)),
        ("Remote", stats.get("remote", 0)),
        ("Avg ATS score", stats.get("avg_ats", "—")),
    ]
    for c, (lbl, val) in zip(cols, items):
        with c:
            st.markdown(metric(lbl, str(val)), unsafe_allow_html=True)
