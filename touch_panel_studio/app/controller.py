from __future__ import annotations

import logging
from dataclasses import dataclass

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from touch_panel_studio.app.context import AppContext
from touch_panel_studio.infrastructure.auth.remember_credentials import clear as clear_remembered_credentials
from touch_panel_studio.infrastructure.auth.remember_credentials import load as load_remembered_credentials
from touch_panel_studio.domain.enums.roles import UserRole
from touch_panel_studio.infrastructure.storage.project_storage import ProjectStorage
from touch_panel_studio.infrastructure.storage.working_dir import load_working_dir, save_working_dir
from touch_panel_studio.ui.windows.first_admin_dialog import FirstAdminDialog
from touch_panel_studio.ui.windows.login import LoginWidget
from touch_panel_studio.ui.windows.project_manager import ProjectManagerWidget
from touch_panel_studio.ui.windows.splash import SplashWidget
from touch_panel_studio.ui.windows.studio import OpenProject, StudioWidget
from touch_panel_studio.ui.windows.working_dir_dialog import WorkingDirDialog

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SessionState:
    user_id: int | None = None
    role: str | None = None


class AppController:
    def __init__(self, ctx: AppContext, window: QMainWindow) -> None:
        self._ctx = ctx
        self._window = window
        self._session = SessionState()
        self._studio: StudioWidget | None = None
        self._skip_auto_login = False

        self._stack = QStackedWidget()
        self._splash = SplashWidget()
        self._login = LoginWidget(ctx, self._on_logged_in)
        self._pm = ProjectManagerWidget(ctx)
        self._viewer_runtime = None  # RuntimeWindow открытый для viewer

        self._stack.addWidget(self._splash)
        self._stack.addWidget(self._login)
        self._stack.addWidget(self._pm)

        self._window.setCentralWidget(self._stack)

        self._pm.open_project.connect(self._on_open_project)
        self._pm.logout_requested.connect(self._on_logout)

    def start(self) -> None:
        self._window.setWindowTitle("Touch Panel Studio")
        # Сразу показываем экран входа — не ждём таймер (на части систем QTimer до exec()
        # ведёт себя непредсказуемо; splash «висел» вечно).
        self._stack.setCurrentWidget(self._login)
        QTimer.singleShot(0, self._center_login_window)
        # Диалог первого админа — после первого цикла event loop, чтобы окно уже было на экране.
        QTimer.singleShot(0, self._post_startup)

    def _center_login_window(self) -> None:
        if self._stack.currentWidget() is not self._login:
            return
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        ag = screen.availableGeometry()
        fg = self._window.frameGeometry()
        fg.moveCenter(ag.center())
        self._window.move(fg.topLeft())

    def _post_startup(self) -> None:
        try:
            self._window.raise_()
            self._window.activateWindow()
            s = self._ctx.app_db.session()
            try:
                has_user = self._ctx.auth.has_any_user(s)
            finally:
                s.close()

            if not has_user:
                dlg = FirstAdminDialog(self._ctx, parent=self._window)
                dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
                dlg.setModal(True)
                dlg.show()
                dlg.raise_()
                dlg.activateWindow()
                dlg.exec()
                s2 = self._ctx.app_db.session()
                try:
                    has_user = self._ctx.auth.has_any_user(s2)
                finally:
                    s2.close()

            if has_user:
                QTimer.singleShot(0, self._try_auto_login)
        except Exception as e:
            logger.exception("Ошибка при старте приложения")
            QMessageBox.critical(
                self._window,
                "Ошибка запуска",
                f"Не удалось проверить пользователей или открыть диалог:\n\n{e}\n\n"
                "Подробности в логе: %LOCALAPPDATA%\\TouchPanelStudio\\logs\\app.log",
            )

    def _try_auto_login(self) -> None:
        if self._skip_auto_login:
            return
        if self._stack.currentWidget() is not self._login:
            return
        creds = load_remembered_credentials(self._ctx.paths.config_dir)
        if not creds:
            return
        u, p = creds
        s = self._ctx.app_db.session()
        try:
            result = self._ctx.auth.authenticate(s, u, p)
        finally:
            s.close()
        if not result.ok or result.user_id is None or result.role is None:
            return
        role_str = result.role.value if hasattr(result.role, "value") else str(result.role)
        try:
            self._on_logged_in(int(result.user_id), str(role_str))
        except Exception as e:
            logger.exception("Автовход")
            QMessageBox.warning(self._window, "Автовход", f"Не удалось выполнить вход:\n{e}")

    def _on_logged_in(self, user_id: int, role: str) -> None:
        # Не менять QStackedWidget из того же стека вызовов, что и clicked() кнопки «Войти» —
        # на части сборок Qt это не даёт отрисовать новый экран.
        QTimer.singleShot(0, lambda: self._apply_after_login(int(user_id), str(role)))

    def _apply_after_login(self, user_id: int, role: str) -> None:
        try:
            self._session.user_id = user_id
            self._session.role = role

            # Проверяем/выбираем рабочую папку перед показом PM
            if not self._ensure_working_dir():
                # Пользователь отказался выбирать — выходим
                return

            self._pm.set_session(user_id=int(user_id), role=str(role))
            self._pm.reload()
            self._stack.setCurrentWidget(self._pm)
            self._stack.update()
            self._pm.update()
            self._window.showMaximized()
            self._window.raise_()
            self._window.activateWindow()
        except Exception as e:
            logger.exception("После входа")
            QMessageBox.critical(self._window, "Ошибка", f"Не удалось открыть список проектов:\n{e}")

    def _ensure_working_dir(self) -> bool:
        """Загружает сохранённую рабочую папку или просит выбрать новую.
        Возвращает False если пользователь отказался (отмена)."""
        config_dir = self._ctx.paths.config_dir
        saved = load_working_dir(config_dir)

        if saved is not None and saved.exists():
            # Папка уже настроена — просто применяем
            self._apply_working_dir(saved)
            return True

        # Папка не задана или не существует — показываем диалог
        dlg = WorkingDirDialog(current=saved, parent=self._window)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        if dlg.exec() != dlg.DialogCode.Accepted or dlg.chosen_path is None:
            return False

        chosen = dlg.chosen_path
        save_working_dir(config_dir, chosen)
        self._apply_working_dir(chosen)
        return True

    def _apply_working_dir(self, path) -> None:
        """Обновляет ProjectStorage на новый путь."""
        from pathlib import Path
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        self._ctx.projects = ProjectStorage(projects_root=p)

    def _on_open_project(self, project_code: str) -> None:
        handle = self._ctx.projects.open_project(project_code)
        role = (self._session.role or "").lower().strip()

        if role == UserRole.viewer.value:
            self._open_as_viewer(handle)
            return

        opened = OpenProject(handle=handle, project_db_engine_title=str(handle.db_file))
        self._studio = StudioWidget(self._ctx, opened)
        self._studio.btn_back.clicked.connect(self._back_to_projects)  # type: ignore[attr-defined]
        self._studio.logout_requested.connect(self._on_logout)
        self._stack.addWidget(self._studio)
        self._stack.setCurrentWidget(self._studio)
        self._window.setWindowTitle(f"Touch Panel Studio — {handle.meta.name} ({handle.meta.code})")

    def _open_as_viewer(self, handle) -> None:  # type: ignore[no-untyped-def]
        from touch_panel_studio.ui.runtime.runtime_window import RuntimeWindow
        project_db = handle.open_db()
        w = RuntimeWindow(project_db=project_db, home_timeout_sec=60, assets_dir=handle.assets_dir)
        self._viewer_runtime = w
        w.destroyed.connect(lambda: setattr(self, "_viewer_runtime", None))
        w.showFullScreen()

    def _back_to_projects(self) -> None:
        self._pm.reload()
        self._stack.setCurrentWidget(self._pm)
        self._window.setWindowTitle("Touch Panel Studio")

    def _on_logout(self) -> None:
        self._session = SessionState()
        self._skip_auto_login = True
        clear_remembered_credentials(self._ctx.paths.config_dir)
        self._pm.set_session(user_id=None, role=None)
        if self._studio is not None:
            self._stack.removeWidget(self._studio)
            self._studio.deleteLater()
            self._studio = None
        self._stack.setCurrentWidget(self._login)
        self._window.setWindowTitle("Touch Panel Studio")
        self._window.showNormal()
        self._window.resize(480, 580)
        QTimer.singleShot(0, self._center_login_window)
        self._window.raise_()
        self._window.activateWindow()
