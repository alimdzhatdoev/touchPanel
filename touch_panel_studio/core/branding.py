"""Путь к логотипу приложения (корень репозитория или PyInstaller _MEIPASS)."""

from __future__ import annotations

from pathlib import Path

from touch_panel_studio.core.paths import bundle_dir

LOGO_FILENAME = "appLogo.png"


def app_logo_path() -> Path | None:
    """
    Файл appLogo.png: при разработке — в корне репозитория (рядом с каталогом touch_panel_studio);
    в frozen-сборке — в корне распакованного bundle (добавьте в datas в .spec).
    """
    bd = bundle_dir()
    if bd is not None:
        p = bd / LOGO_FILENAME
        if p.is_file():
            return p
    # touch_panel_studio/core/branding.py -> родитель родителя родителя = корень репозитория
    root = Path(__file__).resolve().parent.parent.parent
    p = root / LOGO_FILENAME
    if p.is_file():
        return p
    return None
