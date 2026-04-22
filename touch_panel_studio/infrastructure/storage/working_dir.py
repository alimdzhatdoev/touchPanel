"""Сохранение и загрузка пути рабочей папки (где хранятся все проекты и ассеты)."""

from __future__ import annotations

import json
from pathlib import Path


_FILENAME = "working_dir.json"


def save_working_dir(config_dir: Path, working_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / _FILENAME).write_text(
        json.dumps({"path": str(working_dir)}, ensure_ascii=False),
        encoding="utf-8",
    )


def load_working_dir(config_dir: Path) -> Path | None:
    f = config_dir / _FILENAME
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        p = Path(str(data.get("path", "")))
        return p if p and p.is_absolute() else None
    except Exception:
        return None
