from __future__ import annotations

from dataclasses import dataclass

from touch_panel_studio.core.paths import AppPaths
from touch_panel_studio.db.session import SessionFactory
from touch_panel_studio.infrastructure.auth.auth_service import AuthService
from touch_panel_studio.infrastructure.storage.project_storage import ProjectStorage


@dataclass
class AppContext:
    paths: AppPaths
    app_db: SessionFactory
    auth: AuthService
    projects: ProjectStorage

