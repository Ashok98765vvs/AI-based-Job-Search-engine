"""Sidebar filter widget."""
from __future__ import annotations

from typing import Iterable

import streamlit as st


def sidebar_filters(companies: Iterable[str], tech_stack: Iterable[str]) -> dict:
    with st.sidebar:
        st.markdown("### 🔎 Filters")
        remote_only = st.checkbox("Remote only", value=False)
        visa_only = st.checkbox("Visa sponsorship only", value=False)
        salary_min = st.number_input(
            "Min salary (USD)", min_value=0, max_value=500000, value=0, step=10000
        )
        experience = st.select_slider(
            "Experience level",
            options=["Any", "junior", "mid", "senior", "staff", "principal"],
            value="Any",
        )
        chosen_companies = st.multiselect("Companies", sorted(set(companies)))
        chosen_stack = st.multiselect("Tech stack must include", sorted(set(tech_stack)))
        sort_by = st.selectbox(
            "Sort by",
            ["overall", "ats_score", "posted_at", "salary_max"],
            index=0,
        )

    return {
        "remote_only": remote_only,
        "visa_only": visa_only,
        "salary_min": salary_min,
        "experience": experience,
        "companies": chosen_companies,
        "stack": chosen_stack,
        "sort_by": sort_by,
    }
