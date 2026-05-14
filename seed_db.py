"""Seed the SQLite DB with demo jobs (run if DB is empty)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from database import engine, init_db, session_scope
from database.models import Job
from utils.logger import log


def run() -> None:
    init_db()
    with session_scope() as s:
        count = s.query(Job).count()
        if count > 0:
            log.info("DB already has %d jobs — skipping seed.", count)
            return
        seed = Path("database/seed.sql").read_text()
        with engine.begin() as conn:
            for stmt in seed.split(";"):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(text(stmt))
        log.info("Seed inserted.")


if __name__ == "__main__":
    run()
