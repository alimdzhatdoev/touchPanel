"""Поле цвета: ввод hex + кнопка системной палитры."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget


class ColorLineEdit(QWidget):
    """Текст (#hex, transparent, пусто) + кнопка «…» → QColorDialog."""

    editingFinished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line = QLineEdit()
        self._line.setPlaceholderText("#rrggbb или пусто")
        self._line.editingFinished.connect(self.editingFinished.emit)
        self._btn = QPushButton("…")
        self._btn.setFixedWidth(36)
        self._btn.setToolTip("Выбрать цвет из палитры")
        self._btn.clicked.connect(self._open_palette)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._line, 1)
        lay.addWidget(self._btn)

    def _open_palette(self) -> None:
        raw = self._line.text().strip()
        start = QColor("#ffffff")
        if raw and raw.lower() not in ("transparent", "none"):
            c = QColor(raw)
            if c.isValid():
                start = c
        parent = self.window()
        picked = QColorDialog.getColor(
            start, parent, "Цвет", QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if not picked.isValid():
            return
        if picked.alpha() < 255:
            self._line.setText(picked.name(QColor.NameFormat.HexArgb))
        else:
            self._line.setText(picked.name(QColor.NameFormat.HexRgb))
        self.editingFinished.emit()

    def text(self) -> str:
        return self._line.text()

    def setText(self, text: str) -> None:
        self._line.setText(text)

    def setPlaceholderText(self, text: str) -> None:
        self._line.setPlaceholderText(text)

    def setMinimumHeight(self, h: int) -> None:
        self._line.setMinimumHeight(h)
        self._btn.setMinimumHeight(h)

    def line_edit(self) -> QLineEdit:
        return self._line
