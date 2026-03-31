"""Настройки редактора (глобально, в config приложения)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_FILENAME = "editor_settings.json"


@dataclass
class EditorSettings:
    """grid_opacity: 0 = сетка скрыта, 1 = непрозрачные линии."""

    grid_opacity: float = 0.45


def load_editor_settings(config_dir: Path) -> EditorSettings:
    p = config_dir / _FILENAME
    if not p.is_file():
        return EditorSettings()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return EditorSettings()
    g = data.get("grid_opacity", 0.45)
    try:
        gf = float(g)
    except (TypeError, ValueError):
        gf = 0.45
    gf = max(0.0, min(1.0, gf))
    return EditorSettings(grid_opacity=gf)


def save_editor_settings(config_dir: Path, settings: EditorSettings) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    p = config_dir / _FILENAME
    p.write_text(
        json.dumps({"grid_opacity": settings.grid_opacity}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
