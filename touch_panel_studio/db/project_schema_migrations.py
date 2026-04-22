"""Дополнительные столбцы для существующих SQLite БД проектов (create_all не меняет таблицы)."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def apply_project_schema_migrations(engine: Engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("screens"):
        return
    cols = {c["name"] for c in insp.get_columns("screens")}
    stmts: list[str] = []
    if "background_fit" not in cols:
        stmts.append(
            "ALTER TABLE screens ADD COLUMN background_fit VARCHAR(16) NOT NULL DEFAULT 'contain'"
        )
    if "background_scale_percent" not in cols:
        stmts.append(
            "ALTER TABLE screens ADD COLUMN background_scale_percent INTEGER NOT NULL DEFAULT 100"
        )
    if "transition_json" not in cols:
        stmts.append(
            "ALTER TABLE screens ADD COLUMN transition_json TEXT NOT NULL DEFAULT '{}'"
        )

    if not stmts:
        return
    with engine.begin() as conn:
        for sql in stmts:
            conn.execute(text(sql))
