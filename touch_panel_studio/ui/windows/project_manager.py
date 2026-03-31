from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from touch_panel_studio.app.context import AppContext
from touch_panel_studio.domain.enums.roles import UserRole
from touch_panel_studio.infrastructure.storage.project_storage import ProjectHandle, ProjectStorageError
from touch_panel_studio.ui.windows.create_project_dialog import CreateProjectDialog
from touch_panel_studio.infrastructure.import_export.export_service import ProjectExportService
from touch_panel_studio.infrastructure.import_export.import_service import ProjectImportService, ImportError as TPanelImportError
from touch_panel_studio.infrastructure.import_export.migrator import VersionMigrator
from touch_panel_studio.infrastructure.import_export.validator import TemplateValidator
from touch_panel_studio.ui.windows.profile_dialog import ProfileDialog
from touch_panel_studio.ui.windows.user_admin_dialog import UserAdminDialog


class ProjectManagerWidget(QWidget):
    open_project = Signal(str)  # project code
    logout_requested = Signal()

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._user_id: int | None = None
        self._role: str | None = None
        self.setObjectName("ProjectManagerWidget")

        title = QLabel("Проекты")
        title.setStyleSheet("font-size: 22px; font-weight: 650;")

        self.list = QListWidget()
        self.list.setMinimumWidth(520)
        self.list.setStyleSheet("font-size: 16px;")
        self.list.itemDoubleClicked.connect(self._on_open)

        self.btn_create = QPushButton("Создать")
        self.btn_open = QPushButton("Открыть")
        self.btn_import = QPushButton("Импорт…")
        self.btn_export = QPushButton("Экспорт…")
        self.btn_duplicate = QPushButton("Дублировать")
        self.btn_archive = QPushButton("Архивировать")
        self.btn_delete = QPushButton("Удалить")

        for b in (
            self.btn_create,
            self.btn_open,
            self.btn_import,
            self.btn_export,
            self.btn_duplicate,
            self.btn_archive,
            self.btn_delete,
        ):
            b.setMinimumHeight(44)

        self.btn_open.clicked.connect(lambda: self._on_open(self.list.currentItem()))
        self.btn_create.clicked.connect(self._on_create)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_duplicate.clicked.connect(self._on_duplicate)
        self.btn_archive.clicked.connect(self._on_archive)
        self.btn_import.clicked.connect(self._on_import)
        self.btn_export.clicked.connect(self._on_export)

        actions = QVBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self.btn_create)
        actions.addWidget(self.btn_open)
        actions.addSpacing(10)
        actions.addWidget(self.btn_import)
        actions.addWidget(self.btn_export)
        actions.addWidget(self.btn_duplicate)
        actions.addWidget(self.btn_archive)
        actions.addStretch(1)
        self.btn_logout = QPushButton("Выход")
        self.btn_logout.setMinimumHeight(44)
        self.btn_logout.clicked.connect(self.logout_requested.emit)
        actions.addWidget(self.btn_logout)
        self.btn_profile = QPushButton("Мой профиль")
        self.btn_profile.setMinimumHeight(44)
        self.btn_profile.clicked.connect(self._open_profile)
        actions.addWidget(self.btn_profile)
        self.btn_users = QPushButton("Пользователи")
        self.btn_users.setMinimumHeight(44)
        self.btn_users.clicked.connect(self._open_users_admin)
        actions.addWidget(self.btn_users)
        actions.addWidget(self.btn_delete)

        row = QHBoxLayout()
        row.setSpacing(18)
        row.addWidget(self.list, 2)
        row.addLayout(actions, 1)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addLayout(row)
        self.setLayout(layout)

        self.reload()
        self._sync_role_widgets()

    def set_session(self, *, user_id: int | None, role: str | None) -> None:
        self._user_id = int(user_id) if user_id is not None else None
        self._role = str(role) if role is not None else None
        self._sync_role_widgets()

    def _sync_role_widgets(self) -> None:
        is_admin = (self._role or "").lower().strip() == UserRole.admin.value
        self.btn_profile.setEnabled(self._user_id is not None)
        self.btn_users.setVisible(is_admin)
        self.btn_users.setEnabled(is_admin)

    def _open_profile(self) -> None:
        if self._user_id is None:
            return
        dlg = ProfileDialog(self._ctx, user_id=int(self._user_id), parent=self)
        dlg.exec()

    def _open_users_admin(self) -> None:
        if self._user_id is None:
            return
        is_admin = (self._role or "").lower().strip() == UserRole.admin.value
        if not is_admin:
            return
        dlg = UserAdminDialog(self._ctx, actor_user_id=int(self._user_id), parent=self)
        dlg.exec()

    def reload(self) -> None:
        self.list.clear()
        for h in self._ctx.projects.list_projects():
            self._add_project_item(h)

    def _add_project_item(self, h: ProjectHandle) -> None:
        item = QListWidgetItem(f"{h.meta.name}  —  {h.meta.code}")
        item.setData(Qt.UserRole, h.meta.code)
        item.setToolTip(str(h.root_dir))
        self.list.addItem(item)

    def _on_open(self, item: QListWidgetItem | None) -> None:
        if not item:
            return
        code = item.data(Qt.UserRole)
        if code:
            self.open_project.emit(str(code))

    def _selected_code(self) -> str | None:
        item = self.list.currentItem()
        if not item:
            return None
        code = item.data(Qt.UserRole)
        return str(code) if code else None

    def _on_create(self) -> None:
        dlg = CreateProjectDialog()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, code, desc = dlg.values()
        try:
            self._ctx.projects.create_project(name=name, code=code, description=desc)
        except ProjectStorageError as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self.reload()

    def _on_delete(self) -> None:
        code = self._selected_code()
        if not code:
            return
        reply = QMessageBox.question(
            self,
            "Удалить проект",
            f"Удалить проект `{code}`?\n\nПеред удалением будет создан архив-бэкап.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            backups_dir = self._ctx.paths.runtime_dir / "backups" / "projects"
            archive = self._ctx.projects.delete_project(code=code, backup_to=backups_dir)
        except ProjectStorageError as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        QMessageBox.information(self, "Готово", f"Проект удалён.\nБэкап: {archive}")
        self.reload()

    def _on_duplicate(self) -> None:
        code = self._selected_code()
        if not code:
            return
        try:
            self._ctx.projects.duplicate_project(code)
        except ProjectStorageError as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self.reload()

    def _on_archive(self) -> None:
        code = self._selected_code()
        if not code:
            return
        try:
            # Архивирование = бэкап без удаления.
            h = self._ctx.projects.open_project(code)
            backups_dir = self._ctx.paths.runtime_dir / "backups" / "projects"
            backups_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            import shutil

            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_path = backups_dir / f"{h.meta.code}_{ts}.zip"
            tmp_base = backups_dir / f".tmp_zip_{h.meta.code}"
            if tmp_base.exists():
                shutil.rmtree(tmp_base, ignore_errors=True)
            tmp_base.mkdir(parents=True, exist_ok=False)
            try:
                shutil.make_archive(str(tmp_base / h.meta.code), "zip", root_dir=str(h.root_dir))
                produced = tmp_base / f"{h.meta.code}.zip"
                produced.replace(archive_path)
            finally:
                shutil.rmtree(tmp_base, ignore_errors=True)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        QMessageBox.information(self, "Готово", f"Архив создан:\n{archive_path}")

    def _on_export(self) -> None:
        code = self._selected_code()
        if not code:
            QMessageBox.information(self, "Экспорт", "Выберите проект.")
            return
        try:
            h = self._ctx.projects.open_project(code)
        except ProjectStorageError as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт проекта",
            str(self._ctx.paths.runtime_dir),
            "TouchPanel Project (*.tpanel)",
        )
        if not out_path:
            return
        try:
            svc = ProjectExportService()
            out = svc.export_full_project(h, Path(out_path))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        QMessageBox.information(self, "Готово", f"Экспорт завершён:\n{out}")

    def _on_import(self) -> None:
        in_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт проекта",
            str(self._ctx.paths.runtime_dir),
            "TouchPanel Project (*.tpanel)",
        )
        if not in_path:
            return
        try:
            svc = ProjectImportService(
                storage=self._ctx.projects,
                validator=TemplateValidator(),
                migrator=VersionMigrator(),
            )
            handle = svc.import_as_new_project(Path(in_path))
        except (TPanelImportError, Exception) as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))
            return
        QMessageBox.information(self, "Готово", f"Проект импортирован:\n{handle.meta.name} — {handle.meta.code}")
        self.reload()

