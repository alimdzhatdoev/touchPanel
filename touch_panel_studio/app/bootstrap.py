from __future__ import annotations

import logging

from PySide6.QtWidgets import QMainWindow

from touch_panel_studio.core.constants import APP_NAME
from touch_panel_studio.core.logging import configure_logging
from touch_panel_studio.core.paths import AppPaths
from touch_panel_studio.core.security import PasswordService
from touch_panel_studio.db.base import Base
from touch_panel_studio.db.session import SessionFactory
from touch_panel_studio.infrastructure.auth.auth_service import AuthService
from touch_panel_studio.app.context import AppContext
from touch_panel_studio.app.controller import AppController
from touch_panel_studio.infrastructure.storage.project_storage import ProjectStorage

logger = logging.getLogger(__name__)


def bootstrap_app() -> QMainWindow:
    paths = AppPaths.default()
    paths.ensure()
    configure_logging(paths.logs_dir)

    logger.info("Starting %s", APP_NAME)

    # Global app DB (users/settings/templates cache etc.)
    app_db_file = paths.runtime_dir / "app.sqlite3"
    session_factory = SessionFactory.for_sqlite_file(app_db_file)
    Base.metadata.create_all(bind=session_factory.engine)

    # Default first user (requested): admin/admin
    passwords = PasswordService.default()
    auth = AuthService(passwords=passwords)
    with session_factory.session() as s:
        if not auth.has_any_user(s):
            auth.create_first_admin(s, "admin", "admin")

    window = QMainWindow()
    window.setWindowTitle(APP_NAME)
    # Стартовый размер экрана входа; после авторизации контроллер разворачивает окно.
    window.resize(480, 580)

    ctx = AppContext(
        paths=paths,
        app_db=session_factory,
        auth=auth,
        projects=ProjectStorage(projects_root=paths.projects_root),
    )
    controller = AppController(ctx=ctx, window=window)
    controller.start()
    return window

