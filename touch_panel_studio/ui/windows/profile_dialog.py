from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from touch_panel_studio.app.context import AppContext


class ProfileDialog(QDialog):
    def __init__(self, ctx: AppContext, *, user_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._user_id = int(user_id)

        self.setWindowTitle("Мой профиль")
        self.setModal(True)
        self.setMinimumWidth(520)

        self._error = QLabel("")
        self._error.setStyleSheet("color: #b00020;")
        self._error.setWordWrap(True)
        self._error.setVisible(False)

        tabs = QTabWidget()
        tabs.addTab(self._tab_username(), "Логин")
        tabs.addTab(self._tab_password(), "Пароль")

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(tabs)
        layout.addWidget(self._error)
        self.setLayout(layout)

    def _tab_username(self) -> QWidget:
        box = QGroupBox("Сменить логин")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self._u_current_password = QLineEdit()
        self._u_current_password.setEchoMode(QLineEdit.Password)
        self._u_current_password.setPlaceholderText("Текущий пароль")
        self._u_current_password.setMinimumHeight(40)

        self._u_new_username = QLineEdit()
        self._u_new_username.setPlaceholderText("Новый логин (минимум 3 символа)")
        self._u_new_username.setMinimumHeight(40)

        form.addRow("Пароль", self._u_current_password)
        form.addRow("Новый логин", self._u_new_username)

        std = QDialogButtonBox.StandardButton
        buttons = QDialogButtonBox(std.Save)
        buttons.button(std.Save).setText("Сохранить")
        buttons.accepted.connect(self._save_username)

        wrap = QVBoxLayout()
        wrap.setSpacing(12)
        wrap.addLayout(form)
        wrap.addWidget(buttons)
        box.setLayout(wrap)
        return box

    def _tab_password(self) -> QWidget:
        box = QGroupBox("Сменить пароль")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self._p_current_password = QLineEdit()
        self._p_current_password.setEchoMode(QLineEdit.Password)
        self._p_current_password.setPlaceholderText("Текущий пароль")
        self._p_current_password.setMinimumHeight(40)

        self._p_new_password = QLineEdit()
        self._p_new_password.setEchoMode(QLineEdit.Password)
        self._p_new_password.setPlaceholderText("Новый пароль (минимум 5 символов)")
        self._p_new_password.setMinimumHeight(40)

        self._p_new_password2 = QLineEdit()
        self._p_new_password2.setEchoMode(QLineEdit.Password)
        self._p_new_password2.setPlaceholderText("Повторите новый пароль")
        self._p_new_password2.setMinimumHeight(40)

        form.addRow("Текущий пароль", self._p_current_password)
        form.addRow("Новый пароль", self._p_new_password)
        form.addRow("Новый пароль ещё раз", self._p_new_password2)

        std = QDialogButtonBox.StandardButton
        buttons = QDialogButtonBox(std.Save)
        buttons.button(std.Save).setText("Сохранить")
        buttons.accepted.connect(self._save_password)

        wrap = QVBoxLayout()
        wrap.setSpacing(12)
        wrap.addLayout(form)
        wrap.addWidget(buttons)
        box.setLayout(wrap)
        return box

    def _save_username(self) -> None:
        self._error.setVisible(False)
        cur = self._u_current_password.text()
        new_u = self._u_new_username.text()
        with self._ctx.app_db.session() as s:
            res = self._ctx.auth.change_own_username(s, self._user_id, current_password=cur, new_username=new_u)
        if not res.ok:
            self._show_error(res.message)
            return
        self._u_current_password.clear()
        self._u_new_username.clear()

    def _save_password(self) -> None:
        self._error.setVisible(False)
        cur = self._p_current_password.text()
        p1 = self._p_new_password.text()
        p2 = self._p_new_password2.text()
        if p1 != p2:
            self._show_error("Пароли не совпадают.")
            return
        with self._ctx.app_db.session() as s:
            res = self._ctx.auth.change_own_password(s, self._user_id, current_password=cur, new_password=p1)
        if not res.ok:
            self._show_error(res.message)
            return
        self._p_current_password.clear()
        self._p_new_password.clear()
        self._p_new_password2.clear()

    def _show_error(self, msg: str) -> None:
        self._error.setText(msg)
        self._error.setVisible(True)

