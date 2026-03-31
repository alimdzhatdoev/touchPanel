from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    language: Literal["ru"] = "ru"
    kiosk_mode: bool = False
    projects_root: Path | None = None

    autosave_enabled: bool = True
    autosave_interval_sec: int = Field(default=10, ge=3, le=120)

    runtime_home_timeout_sec: int = Field(default=60, ge=5, le=24 * 60 * 60)

