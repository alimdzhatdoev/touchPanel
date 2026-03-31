from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from touch_panel_studio.core.constants import DEFAULT_APPDATA_DIRNAME, DEFAULT_PROJECTS_DIRNAME


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path | None:
    """Каталог распакованного onefile/ресурсов PyInstaller (если есть)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return None


def _windows_appdata_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not base:
        return Path.home() / "AppData" / "Local"
    return Path(base)


@dataclass(frozen=True, slots=True)
class AppPaths:
    appdata_dir: Path
    logs_dir: Path
    config_dir: Path
    runtime_dir: Path
    projects_root: Path

    @staticmethod
    def default() -> "AppPaths":
        appdata_dir = _windows_appdata_dir() / DEFAULT_APPDATA_DIRNAME
        return AppPaths(
            appdata_dir=appdata_dir,
            logs_dir=appdata_dir / "logs",
            config_dir=appdata_dir / "config",
            runtime_dir=appdata_dir / "runtime",
            projects_root=appdata_dir / DEFAULT_PROJECTS_DIRNAME,
        )

    def ensure(self) -> None:
        for p in (self.appdata_dir, self.logs_dir, self.config_dir, self.runtime_dir, self.projects_root):
            p.mkdir(parents=True, exist_ok=True)

