"""Виджеты с той же отрисовкой, что на канвасе редактора (WYSIWYG при запуске)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QPushButton, QWidget

from touch_panel_studio.ui.common.component_canvas_paint import (
    paint_button_component,
    paint_image_component,
    paint_rounded_rect,
    paint_shape_ellipse,
    paint_shape_line,
    paint_text_component,
)


class _MirrorPaintWidget(QWidget):
    def __init__(self, parent: QWidget | None, style: dict) -> None:
        super().__init__(parent)
        self._style = style
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def _begin_paint(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        op = float(self._style.get("opacity", 1.0))
        painter.setOpacity(max(0.0, min(1.0, op)))


class RuntimeMirrorTextWidget(_MirrorPaintWidget):
    def __init__(self, parent: QWidget | None, props: dict, style: dict, *, default_text: str) -> None:
        super().__init__(parent, style)
        self._props = props
        self._default_text = default_text

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self._begin_paint(p)
        txt = str(self._props.get("text", self._default_text))
        paint_text_component(p, QRectF(self.rect()), txt, self._style)


class RuntimeMirrorShapeRectWidget(_MirrorPaintWidget):
    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        p = QPainter(self)
        self._begin_paint(p)
        paint_rounded_rect(p, QRectF(self.rect()), self._style, fill=True, stroke=True)


class RuntimeMirrorShapeEllipseWidget(_MirrorPaintWidget):
    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        p = QPainter(self)
        self._begin_paint(p)
        paint_shape_ellipse(p, QRectF(self.rect()), self._style)


class RuntimeMirrorShapeLineWidget(_MirrorPaintWidget):
    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        p = QPainter(self)
        self._begin_paint(p)
        paint_shape_line(p, QRectF(self.rect()), self._style)


class RuntimeMirrorImageWidget(_MirrorPaintWidget):
    def __init__(self, parent: QWidget | None, style: dict, pixmap: QPixmap | None) -> None:
        super().__init__(parent, style)
        self._pixmap = pixmap

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        p = QPainter(self)
        self._begin_paint(p)
        paint_image_component(p, QRectF(self.rect()), style=self._style, pixmap=self._pixmap)


class RuntimeMirrorButton(QPushButton):
    def __init__(
        self,
        parent: QWidget | None,
        props: dict,
        style: dict,
        *,
        default_label: str,
        icon_pixmap: QPixmap | None,
        background_pixmap: QPixmap | None,
    ) -> None:
        super().__init__(parent)
        self._props = props
        self._style = style
        self._default_label = default_label
        self._icon_pm = icon_pixmap
        self._bg_pm = background_pixmap
        self.setFlat(True)
        self.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0px; }")

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        op = float(self._style.get("opacity", 1.0))
        p.setOpacity(max(0.0, min(1.0, op)))
        label = str(self._props.get("text", self._default_label))
        paint_button_component(
            p,
            QRectF(self.rect()),
            label=label,
            style=self._style,
            icon_pixmap=self._icon_pm,
            background_pixmap=self._bg_pm,
        )
