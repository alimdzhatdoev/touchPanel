from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QCheckBox,
    QComboBox,
    QVBoxLayout,
    QWidget,
)

from touch_panel_studio.app.context import AppContext
from touch_panel_studio.domain.enums.roles import UserRole


class _UserEditDialog(QDialog):
    def __init__(
        self,
        ctx: AppContext,
        *,
        actor_user_id: int,
        target_user_id: int | None,
        username: str = "",
        role: str = "viewer",
        is_active: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._actor_user_id = int(actor_user_id)
        self._target_user_id = int(target_user_id) if target_user_id is not None else None

        self.setWindowTitle("Пользователь" if target_user_id else "Новый пользователь")
        self.setModal(True)
        self.setMinimumWidth(520)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #b00020;")
        self._error.setWordWrap(True)
        self._error.setVisible(False)

        self.username = QLineEdit()
        self.username.setMinimumHeight(40)
        self.username.setPlaceholderText("Логин")
        self.username.setText(username)

        self.role = QComboBox()
        self.role.setMinimumHeight(36)
        self.role.addItem("admin", "admin")
        self.role.addItem("editor", "editor")
        self.role.addItem("viewer", "viewer")
        self.role.addItem("service", "service")
        ix = self.role.findData(str(role))
        self.role.setCurrentIndex(ix if ix >= 0 else 2)

        self.active = QCheckBox("Активен")
        self.active.setChecked(bool(is_active))

        self.new_password = QLineEdit()
        self.new_password.setMinimumHeight(40)
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setPlaceholderText("Новый пароль (оставьте пустым, чтобы не менять)")

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow("Логин", self.username)
        form.addRow("Роль", self.role)
        form.addRow("", self.active)
        form.addRow("Пароль", self.new_password)

        std = QDialogButtonBox.StandardButton
        buttons = QDialogButtonBox(std.Save | std.Cancel)
        buttons.button(std.Save).setText("Сохранить")
        buttons.button(std.Cancel).setText("Отмена")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _save(self) -> None:
        self._error.setVisible(False)
        uname = self.username.text()
        role = str(self.role.currentData())
        active = bool(self.active.isChecked())
        pwd = self.new_password.text()

        with self._ctx.app_db.session() as s:
            if self._target_user_id is None:
                res = self._ctx.auth.admin_create_user(
                    s,
                    self._actor_user_id,
                    username=uname,
                    password=pwd,
                    role=UserRole(role),
                    is_active=active,
                )
            else:
                res = self._ctx.auth.admin_update_user(
                    s,
                    self._actor_user_id,
                    int(self._target_user_id),
                    username=uname,
                    role=UserRole(role),
                    is_active=active,
                    new_password=pwd if pwd.strip() else None,
                )
        if not res.ok:
            self._error.setText(res.message)
            self._error.setVisible(True)
            return
        self.accept()


class UserAdminDialog(QDialog):
    def __init__(self, ctx: AppContext, *, actor_user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._actor_user_id = int(actor_user_id)

        self.setWindowTitle("Пользователи")
        self.setModal(True)
        self.setMinimumWidth(720)
        self.setMinimumHeight(520)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _=None: self._edit_selected())

        self.btn_new = QPushButton("Создать…")
        self.btn_edit = QPushButton("Изменить…")
        self.btn_refresh = QPushButton("Обновить")
        for b in (self.btn_new, self.btn_edit, self.btn_refresh):
            b.setMinimumHeight(40)
        self.btn_new.clicked.connect(self._new_user)
        self.btn_edit.clicked.connect(self._edit_selected)
        self.btn_refresh.clicked.connect(self._reload)

        actions = QVBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self.btn_new)
        actions.addWidget(self.btn_edit)
        actions.addWidget(self.btn_refresh)
        actions.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self.list, 2)
        row.addLayout(actions, 1)

        wrap = QGroupBox("Список пользователей")
        wrap_l = QVBoxLayout()
        wrap_l.setContentsMargins(12, 12, 12, 12)
        wrap_l.addLayout(row)
        wrap.setLayout(wrap_l)

        std = QDialogButtonBox.StandardButton
        buttons = QDialogButtonBox(std.Close)
        buttons.button(std.Close).setText("Закрыть")
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(wrap, 1)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self._reload()

    def _reload(self) -> None:
        self.list.clear()
        with self._ctx.app_db.session() as s:
            res, users = self._ctx.auth.list_users(s, self._actor_user_id)
        if not res.ok:
            QMessageBox.critical(self, "Ошибка", res.message)
            return
        for u in users:
            role = u.role.value if hasattr(u.role, "value") else str(u.role)
            st = "активен" if u.is_active else "выкл"
            item = QListWidgetItem(f"{u.username}   • {role}   • {st}   • id={u.id}")
            item.setData(Qt.UserRole, int(u.id))
            self.list.addItem(item)

    def _selected_user_id(self) -> int | None:
        it = self.list.currentItem()
        if not it:
            return None
        v = it.data(Qt.UserRole)
        return int(v) if v is not None else None

    def _new_user(self) -> None:
        dlg = _UserEditDialog(self._ctx, actor_user_id=self._actor_user_id, target_user_id=None, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload()

    def _edit_selected(self) -> None:
        uid = self._selected_user_id()
        if not uid:
            return
        with self._ctx.app_db.session() as s:
            res, users = self._ctx.auth.list_users(s, self._actor_user_id)
        if not res.ok:
            QMessageBox.critical(self, "Ошибка", res.message)
            return
        u = next((x for x in users if int(x.id) == int(uid)), None)
        if u is None:
            return
        role = u.role.value if hasattr(u.role, "value") else str(u.role)
        dlg = _UserEditDialog(
            self._ctx,
            actor_user_id=self._actor_user_id,
            target_user_id=int(u.id),
            username=str(u.username),
            role=str(role),
            is_active=bool(u.is_active),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload()

