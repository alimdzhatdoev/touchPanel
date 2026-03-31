from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from touch_panel_studio.app.context import AppContext
from touch_panel_studio.infrastructure.auth.remember_credentials import clear as clear_remembered
from touch_panel_studio.infrastructure.auth.remember_credentials import save as save_remembered


class LoginWidget(QWidget):
    """on_logged_in вызывается синхронно после успешной проверки (без Signal — надёжнее на Windows)."""

    def __init__(self, ctx: AppContext, on_logged_in: Callable[[int, str], None]) -> None:
        super().__init__()
        self._ctx = ctx
        self._on_logged_in = on_logged_in
        self.setObjectName("LoginWidget")

        title = QLabel("Вход")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 650;")

        self.username = QLineEdit()
        self.username.setPlaceholderText("Логин")
        self.username.setMinimumHeight(44)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Пароль")
        self.password.setMinimumHeight(44)

        self.remember = QCheckBox("Запомнить меня (24 часа)")
        self.remember.setStyleSheet("font-size: 14px;")

        self.error = QLabel("")
        self.error.setStyleSheet("color: #b00020;")
        self.error.setWordWrap(True)
        self.error.setVisible(False)

        self.login_btn = QPushButton("Войти")
        self.login_btn.setMinimumHeight(48)
        self.login_btn.clicked.connect(self._on_login_clicked)

        self.password.returnPressed.connect(self._on_login_clicked)
        self.username.returnPressed.connect(self.password.setFocus)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(12)
        grid.addWidget(QLabel("Логин"), 0, 0)
        grid.addWidget(self.username, 0, 1)
        grid.addWidget(QLabel("Пароль"), 1, 0)
        grid.addWidget(self.password, 1, 1)

        form_col = QVBoxLayout()
        form_col.setSpacing(12)
        form_col.addWidget(title)
        form_col.addSpacing(4)
        form_col.addLayout(grid)
        form_col.addWidget(self.remember)
        form_col.addWidget(self.error)
        form_col.addWidget(self.login_btn)

        form_wrap = QWidget()
        form_wrap.setLayout(form_col)
        form_wrap.setMaximumWidth(420)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(form_wrap, 0)
        row.addStretch(1)

        box = QVBoxLayout()
        box.setContentsMargins(32, 40, 32, 40)
        box.setSpacing(0)
        box.addStretch(1)
        box.addLayout(row)
        box.addStretch(2)
        self.setLayout(box)

    def _on_login_clicked(self) -> None:
        self.error.setVisible(False)

        u = self.username.text()
        p = self.password.text()
        s = self._ctx.app_db.session()
        try:
            result = self._ctx.auth.authenticate(s, u, p)
        finally:
            s.close()

        if not result.ok or result.user_id is None or result.role is None:
            self._show_error(result.message if result.message else "Ошибка входа.")
            return

        if self.remember.isChecked():
            save_remembered(self._ctx.paths.config_dir, u, p)
        else:
            clear_remembered(self._ctx.paths.config_dir)

        role_str = result.role.value if hasattr(result.role, "value") else str(result.role)
        try:
            self._on_logged_in(int(result.user_id), str(role_str))
        except Exception as e:
            self._show_error(f"Не удалось перейти к проектам: {e}")
            return

        self.password.clear()

    def _show_error(self, msg: str) -> None:
        self.error.setText(msg)
        self.error.setVisible(True)
