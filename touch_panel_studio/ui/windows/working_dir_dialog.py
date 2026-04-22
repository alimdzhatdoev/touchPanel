"""Диалог выбора рабочей папки при первом запуске или смене пути."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class WorkingDirDialog(QDialog):
    """Показывается после логина, если рабочая папка ещё не выбрана.

    Рабочая папка — это директория, в которой программа хранит все проекты
    и медиафайлы. Можно указать сетевой диск, USB или любую другую папку —
    тогда достаточно подключить это хранилище на другом устройстве и всё будет доступно.
    """

    def __init__(self, current: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выбор рабочей папки")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(560)
        self._chosen: Path | None = current

        header = QLabel("Рабочая папка")
        header.setStyleSheet("font-size: 17px; font-weight: 650;")

        info = QLabel(
            "Программа хранит все проекты и медиафайлы в одной папке.\n"
            "Укажите её — например, папку на сетевом диске или USB-накопителе.\n"
            "На любом другом устройстве достаточно подключить то же хранилище\n"
            "и указать ту же папку — все проекты сразу появятся в списке."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #aaaaaa; margin-bottom: 8px;")

        path_label = QLabel("Папка:")
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Выберите папку или введите путь вручную…")
        self._path_edit.setReadOnly(False)
        if current:
            self._path_edit.setText(str(current))

        btn_browse = QPushButton("Обзор…")
        btn_browse.setFixedWidth(100)
        btn_browse.clicked.connect(self._browse)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(self._path_edit, 1)
        path_row.addWidget(btn_browse)

        note = QLabel(
            "Папка будет создана автоматически, если не существует.\n"
            "Путь сохраняется на этом устройстве — на других нужно выбрать заново."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 12px; color: #888888; margin-top: 4px;")

        btn_ok = QPushButton("Подтвердить")
        btn_ok.setMinimumHeight(44)
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._accept)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setMinimumHeight(44)
        btn_cancel.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(header)
        layout.addWidget(info)
        layout.addWidget(path_label)
        layout.addLayout(path_row)
        layout.addWidget(note)
        layout.addSpacing(8)
        layout.addLayout(btn_row)

    def _browse(self) -> None:
        start = self._path_edit.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Выберите рабочую папку", start)
        if chosen:
            self._path_edit.setText(chosen)

    def _accept(self) -> None:
        raw = self._path_edit.text().strip()
        if not raw:
            QMessageBox.warning(self, "Папка не выбрана", "Укажите путь к рабочей папке.")
            return
        p = Path(raw)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать папку:\n{e}")
            return
        self._chosen = p
        self.accept()

    @property
    def chosen_path(self) -> Path | None:
        return self._chosen
