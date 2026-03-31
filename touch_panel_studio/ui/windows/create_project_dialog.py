from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)


class CreateProjectDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Создать проект")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Например: Панель холла")
        self.name.setMinimumHeight(40)

        self.code = QLineEdit()
        self.code.setPlaceholderText("Оставьте пустым для авто-генерации (proj-xxxxxxxx)")
        self.code.setMinimumHeight(40)

        self.description = QTextEdit()
        self.description.setPlaceholderText("Описание (необязательно)")
        self.description.setMinimumHeight(120)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow("Название", self.name)
        form.addRow("Код", self.code)
        form.addRow("Описание", self.description)

        # Qt6: StandardButton.Create нет — используем Ok и подписываем «Создать»
        std = QDialogButtonBox.StandardButton
        buttons = QDialogButtonBox(std.Ok | std.Cancel)
        buttons.button(std.Ok).setText("Создать")
        buttons.button(std.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def values(self) -> tuple[str, str | None, str | None]:
        name = self.name.text().strip()
        code = self.code.text().strip() or None
        desc = self.description.toPlainText().strip() or None
        return name, code, desc

