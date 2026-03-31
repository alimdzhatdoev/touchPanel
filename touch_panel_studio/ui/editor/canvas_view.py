from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QBrush
from PySide6.QtWidgets import QGraphicsView, QSizePolicy


class CanvasView(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(120, 120)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # ВАЖНО: QGraphicsView рисует фон сцены только если backgroundBrush == NoBrush.
        # Иначе Qt заливает viewport белым и НЕ вызывает QGraphicsScene.drawBackground() —
        # картинка фона и сетка в GridScene не появляются.
        self.setBackgroundBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.viewport().setAutoFillBackground(False)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, "delete_selected"):
                    parent.delete_selected()  # type: ignore[attr-defined]
                    event.accept()
                    return
                parent = parent.parent()
        return super().keyPressEvent(event)

