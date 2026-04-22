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
        # Хранит размытый снимок ВСЕГО фона экрана.
        # В paintEvent кропаем по текущей позиции виджета — так блюр
        # корректно следует за компонентом при анимации движения.
        self._backdrop_source: QPixmap | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_backdrop_source(self, full_blurred_pm: QPixmap | None) -> None:
        """Передаёт размытый снимок всего фона (весь экран).
        Кроп по текущей позиции делается динамически в paintEvent."""
        self._backdrop_source = full_blurred_pm
        self.update()

    def _draw_backdrop(self, painter: QPainter) -> None:
        if self._backdrop_source is None or self._backdrop_source.isNull():
            return
        pos = self.pos()
        crop = self._backdrop_source.copy(pos.x(), pos.y(), self.width(), self.height())
        painter.save()
        painter.setOpacity(1.0)
        painter.drawPixmap(0, 0, crop)
        painter.restore()

    def _begin_paint(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._draw_backdrop(painter)
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
        self._backdrop_source: QPixmap | None = None
        self.setFlat(True)
        self.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0px; }")

    def set_backdrop_source(self, full_blurred_pm: QPixmap | None) -> None:
        """Передаёт размытый снимок всего фона; кроп по позиции — динамически."""
        self._backdrop_source = full_blurred_pm
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        # Backdrop: кропаем по текущей позиции — корректно при анимации
        if self._backdrop_source is not None and not self._backdrop_source.isNull():
            pos = self.pos()
            crop = self._backdrop_source.copy(pos.x(), pos.y(), self.width(), self.height())
            p.save()
            p.setOpacity(1.0)
            p.drawPixmap(0, 0, crop)
            p.restore()
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
