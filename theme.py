"""Inject dark-mode styling, animations and typography."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
:root {
    --bg: #0b1020;
    --panel: #121833;
    --panel-2: #161e3f;
    --text: #e7ecff;
    --muted: #9aa4c7;
    --accent: #7c5cff;
    --accent-2: #21d4fd;
    --success: #2bd4a4;
    --warn: #ffb347;
    --danger: #ff6b81;
    --border: rgba(255,255,255,0.08);
}
html, body, [data-testid="stAppViewContainer"], .main {
    background: radial-gradient(1200px 600px at 0% -10%, #1a1f4d 0%, transparent 50%),
                radial-gradient(900px 500px at 100% 0%, #093243 0%, transparent 50%),
                var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1020, #0a0e22) !important;
    border-right: 1px solid var(--border);
}
h1, h2, h3, h4 { color: var(--text) !important; letter-spacing: -0.01em; }
.metric-card {
    background: linear-gradient(135deg, var(--panel), var(--panel-2));
    border: 1px solid var(--border);
    padding: 18px 20px;
    border-radius: 16px;
    box-shadow: 0 6px 24px rgba(0,0,0,0.25);
}
.metric-card .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; }
.metric-card .value { font-size: 28px; font-weight: 700; margin-top: 4px; background: linear-gradient(90deg,#7c5cff,#21d4fd); -webkit-background-clip: text; color: transparent; }

.job-card {
    background: linear-gradient(180deg, var(--panel), var(--panel-2));
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 18px 20px;
    margin-bottom: 14px;
    transition: transform .15s ease, border-color .15s ease, box-shadow .2s ease;
    animation: fadeUp .35s ease both;
}
.job-card:hover { transform: translateY(-2px); border-color: rgba(124,92,255,0.4); box-shadow: 0 10px 30px rgba(124,92,255,0.15); }
.job-card .title { font-weight: 700; font-size: 18px; }
.job-card .meta { color: var(--muted); font-size: 13px; margin-top: 4px; }
.job-card .badges { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    background: rgba(124,92,255,0.15);
    color: #cfc4ff;
    border: 1px solid rgba(124,92,255,0.25);
}
.badge.success { background: rgba(43,212,164,0.12); color: #aaf3da; border-color: rgba(43,212,164,0.3); }
.badge.warn    { background: rgba(255,179,71,0.12); color: #ffd9a6; border-color: rgba(255,179,71,0.3); }
.badge.danger  { background: rgba(255,107,129,0.12); color: #ffc5cf; border-color: rgba(255,107,129,0.3); }
.badge.info    { background: rgba(33,212,253,0.12); color: #b6efff; border-color: rgba(33,212,253,0.3); }

.score-ring {
    --p: 0;
    width: 64px; height: 64px;
    border-radius: 50%;
    background:
        conic-gradient(#7c5cff calc(var(--p)*1%), rgba(255,255,255,0.07) 0);
    display: grid; place-items: center;
    font-weight: 700; color: var(--text);
    box-shadow: inset 0 0 0 6px var(--panel);
}

.apply-link a {
    color: #fff !important;
    background: linear-gradient(90deg,#7c5cff,#21d4fd);
    padding: 8px 14px;
    border-radius: 999px;
    font-weight: 600;
    text-decoration: none !important;
    display: inline-block;
    margin-top: 10px;
}

@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse  { 0%,100% { opacity: 1; } 50% { opacity: .55; } }
.loading-dot { animation: pulse 1.2s infinite; color: var(--accent-2); }
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
