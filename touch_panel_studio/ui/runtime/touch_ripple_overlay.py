"""Минималистичный индикатор касания для тач-панели."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QElapsedTimer, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

_DURATION_MS = 400
_MAX_RADIUS = 36.0   # небольшое кольцо — ровно вокруг пальца
_RING_WIDTH = 1.5


@dataclass
class _Ripple:
    cx: float
    cy: float
    _clock: QElapsedTimer = field(default_factory=QElapsedTimer, init=False, repr=False)

    def __post_init__(self) -> None:
        self._clock.start()

    @property
    def t(self) -> float:
        return min(1.0, self._clock.elapsed() / _DURATION_MS)

    @property
    def done(self) -> bool:
        return self._clock.elapsed() >= _DURATION_MS


class TouchRippleOverlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.raise_()

        self._ripples: list[_Ripple] = []
        self._timer = QTimer(self)
        self._timer.setInterval(14)
        self._timer.timeout.connect(self._tick)

    def spawn(self, pos: QPointF) -> None:
        self._ripples.append(_Ripple(pos.x(), pos.y()))
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self) -> None:
        self._ripples = [r for r in self._ripples if not r.done]
        if not self._ripples:
            self._timer.stop()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        if not self._ripples:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setBrush(Qt.BrushStyle.NoBrush)

        for r in self._ripples:
            t = r.t
            # ease-out: быстро расширяется, плавно останавливается
            ease = 1.0 - (1.0 - t) ** 2
            radius = _MAX_RADIUS * ease

            # Прозрачность: появляется сразу, затухает во второй половине
            if t < 0.25:
                alpha = int(180 * (t / 0.25))
            else:
                alpha = int(180 * (1.0 - (t - 0.25) / 0.75))

            col = QColor(255, 255, 255, alpha)
            pen = QPen(col)
            pen.setWidthF(_RING_WIDTH)
            p.setPen(pen)
            p.drawEllipse(QPointF(r.cx, r.cy), radius, radius)

        p.end()


class _TapFilter(QObject):
    def __init__(self, window: QWidget, overlay: TouchRippleOverlay) -> None:
        super().__init__()
        self._window = window
        self._overlay = overlay

    def eventFilter(self, obj: QObject, event) -> bool:  # type: ignore[override]
        from PySide6.QtCore import QEvent
        widget = obj if isinstance(obj, QWidget) else None
        if widget is None:
            return False
        t = event.type()
        if t == QEvent.Type.MouseButtonPress and widget.window() is self._window:
            gpos = widget.mapToGlobal(event.position().toPoint())
            self._overlay.spawn(QPointF(self._window.mapFromGlobal(gpos)))
        elif t == QEvent.Type.TouchBegin and widget.window() is self._window:
            for pt in event.points():
                gpos = pt.globalPosition().toPoint()
                self._overlay.spawn(QPointF(self._window.mapFromGlobal(gpos)))
        return False


def install_ripple(window: QWidget) -> TouchRippleOverlay:
    overlay = TouchRippleOverlay(window)
    overlay.resize(window.size())
    overlay.raise_()
    f = _TapFilter(window, overlay)
    window._tap_filter = f  # type: ignore[attr-defined]
    QApplication.instance().installEventFilter(f)  # type: ignore[union-attr]
    return overlay
