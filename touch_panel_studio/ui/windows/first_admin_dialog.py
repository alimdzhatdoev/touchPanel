from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from touch_panel_studio.app.context import AppContext


class FirstAdminDialog(QDialog):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx

        self.setWindowTitle("Первый запуск — создание администратора")
        self.setModal(True)
        self.setMinimumWidth(520)

        header = QLabel("Создайте главного администратора")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")

        hint = QLabel("Пароль хранится только в виде хеша (Argon2).")
        hint.setStyleSheet("color: #666;")
        hint.setWordWrap(True)

        self.username = QLineEdit()
        self.username.setPlaceholderText("admin")
        self.username.setMinimumHeight(40)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Минимум 5 символов")
        self.password.setMinimumHeight(40)

        self.password2 = QLineEdit()
        self.password2.setEchoMode(QLineEdit.Password)
        self.password2.setPlaceholderText("Повторите пароль")
        self.password2.setMinimumHeight(40)

        self.error = QLabel("")
        self.error.setStyleSheet("color: #b00020;")
        self.error.setWordWrap(True)
        self.error.setVisible(False)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow("Логин", self.username)
        form.addRow("Пароль", self.password)
        form.addRow("Пароль ещё раз", self.password2)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Создать")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_create_clicked)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(header)
        layout.addWidget(hint)
        layout.addSpacing(8)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _on_create_clicked(self) -> None:
        u = self.username.text().strip()
        p1 = self.password.text()
        p2 = self.password2.text()
        if p1 != p2:
            self._show_error("Пароли не совпадают.")
            return

        with self._ctx.app_db.session() as s:
            result = self._ctx.auth.create_first_admin(s, u, p1)

        if not result.ok:
            self._show_error(result.message)
            return

        self.accept()

    def _show_error(self, msg: str) -> None:
        self.error.setText(msg)
        self.error.setVisible(True)

