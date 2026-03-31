"""Обёртка: макет экрана фиксированного размера масштабируется на весь виджет (как превью на весь монитор)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsView,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class RuntimeScaledScreen(QWidget):
    def __init__(self, design_w: int, design_h: int, inner: QWidget) -> None:
        super().__init__()
        self._dw = max(1, int(design_w))
        self._dh = max(1, int(design_h))

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(0, 0, float(self._dw), float(self._dh))

        self._view = QGraphicsView(self._scene)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setFrameShape(QFrame.Shape.NoFrame)
        self._view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._view.setBackgroundBrush(QBrush(QColor("#000000")))
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        proxy = QGraphicsProxyWidget()
        proxy.setWidget(inner)
        proxy.setPos(0, 0)
        self._scene.addItem(proxy)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._view, 1)

        QTimer.singleShot(0, self._fit)

    def _fit(self) -> None:
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._fit()
