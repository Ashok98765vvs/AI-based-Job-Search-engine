"""Export job result sets to CSV / XLSX / JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd

EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def _to_df(jobs: Iterable[dict]) -> pd.DataFrame:
    return pd.DataFrame(list(jobs))


def to_csv(jobs: Iterable[dict], filename: str = "jobs.csv") -> Path:
    path = EXPORT_DIR / filename
    _to_df(jobs).to_csv(path, index=False)
    return path


def to_xlsx(jobs: Iterable[dict], filename: str = "jobs.xlsx") -> Path:
    path = EXPORT_DIR / filename
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        _to_df(jobs).to_excel(writer, sheet_name="Jobs", index=False)
    return path


def to_json(jobs: Iterable[dict], filename: str = "jobs.json") -> Path:
    path = EXPORT_DIR / filename
    path.write_text(json.dumps(list(jobs), indent=2, default=str))
    return path
