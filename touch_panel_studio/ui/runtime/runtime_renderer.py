from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QRectF, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QPushButton,
    QWidget,
)

from touch_panel_studio.db.models.component import Component
from touch_panel_studio.db.models.screen import Screen
from touch_panel_studio.infrastructure.storage.asset_paths import load_pixmap_from_file, resolve_asset_file
from touch_panel_studio.ui.common.background_compose import compose_screen_background_pixmap
from touch_panel_studio.ui.common.component_canvas_paint import blur_pixmap as _blur_pixmap_fn
from touch_panel_studio.ui.runtime.runtime_mirror_widgets import (
    RuntimeMirrorButton,
    RuntimeMirrorImageWidget,
    RuntimeMirrorShapeEllipseWidget,
    RuntimeMirrorShapeLineWidget,
    RuntimeMirrorShapeRectWidget,
    RuntimeMirrorTextWidget,
)
from touch_panel_studio.ui.runtime.runtime_scaled_screen import RuntimeScaledScreen


@dataclass(frozen=True, slots=True)
class RuntimeComponentView:
    component_id: int
    widget: QWidget


def _safe_json(s: str) -> dict:
    try:
        v = json.loads(s or "{}")
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


@dataclass
class _AnimEntry:
    widget: QWidget
    orig_geom: QRect
    anim_type: str
    delay_ms: int
    duration_ms: int
    # Keeps references to running animations so GC doesn't collect them
    _active: list = field(default_factory=list)


def _start_pos_for(anim_type: str, orig: QRect) -> QPoint:
    ox, oy, ow, oh = orig.x(), orig.y(), orig.width(), orig.height()
    if anim_type == "slide_left":
        return QPoint(ox - ow, oy)
    if anim_type == "slide_right":
        return QPoint(ox + ow, oy)
    if anim_type == "slide_up":
        return QPoint(ox, oy - oh)
    if anim_type == "slide_down":
        return QPoint(ox, oy + oh)
    return QPoint(ox, oy)


def _apply_initial_state(entry: _AnimEntry) -> None:
    """Переводит виджет в начальное скрытое состояние до начала анимации.

    Для fade/zoom — opacity=0 (виджет на месте, прозрачный).
    Для слайдов   — setVisible(False); при старте анимации снова покажем.
    Вызывается ДО задержки (delay), чтобы объект не торчал видимым во время паузы.
    """
    w = entry.widget
    anim_type = entry.anim_type
    orig = entry.orig_geom

    if anim_type in ("fade", "zoom"):
        w.setGeometry(orig)
        w.setVisible(True)
        effect = QGraphicsOpacityEffect(w)
        effect.setOpacity(0.0)
        w.setGraphicsEffect(effect)

    elif anim_type in ("slide_left", "slide_right", "slide_up", "slide_down"):
        w.setGeometry(orig)   # финальная геометрия, но скрыт
        w.setGraphicsEffect(None)
        w.setVisible(False)   # прячем — двигаться начнём только при старте


class ScreenAnimController:
    """Запускает / повторяет анимации появления компонентов на экране."""

    def __init__(self, entries: list[_AnimEntry]) -> None:
        self._entries = entries
        self._timers: list[QTimer] = []

    def reset(self) -> None:
        """Останавливает активные анимации и сбрасывает виджеты в начальное состояние.
        Должен вызываться ДО показа экрана (до setCurrentWidget), чтобы не было мигания.
        """
        for t in self._timers:
            t.stop()
        self._timers.clear()
        for entry in self._entries:
            if entry.anim_type != "none":
                entry._active.clear()
                _apply_initial_state(entry)

    def play(self) -> None:
        """Запускает анимации. Предполагается что reset() уже вызван."""
        for entry in self._entries:
            if entry.anim_type == "none":
                continue
            if entry.delay_ms > 0:
                t = QTimer()
                t.setSingleShot(True)
                t.timeout.connect(lambda e=entry: self._start_one(e))
                t.start(entry.delay_ms)
                self._timers.append(t)
            else:
                self._start_one(entry)

    def _start_one(self, entry: _AnimEntry) -> None:
        """Показывает виджет и запускает анимацию от начальной позиции к финальной."""
        w = entry.widget
        anim_type = entry.anim_type
        duration = entry.duration_ms
        orig = entry.orig_geom

        if anim_type in ("fade", "zoom"):
            effect = w.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(w)
                effect.setOpacity(0.0)
                w.setGraphicsEffect(effect)
            easing = QEasingCurve.Type.OutBack if anim_type == "zoom" else QEasingCurve.Type.OutCubic
            anim = QPropertyAnimation(effect, b"opacity", w)
            anim.setDuration(duration)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(easing)
            entry._active.append(anim)
            anim.start()

        elif anim_type in ("slide_left", "slide_right", "slide_up", "slide_down"):
            start_pos = _start_pos_for(anim_type, orig)
            end_pos = QPoint(orig.x(), orig.y())
            # Переставляем на стартовую позицию и показываем
            w.move(start_pos)
            w.setVisible(True)
            anim = QPropertyAnimation(w, b"pos", w)
            anim.setDuration(duration)
            anim.setStartValue(start_pos)
            anim.setEndValue(end_pos)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            entry._active.append(anim)
            anim.start()


def _blur_pixmap(pixmap: QPixmap, radius: float) -> QPixmap:
    return _blur_pixmap_fn(pixmap, radius)


class RuntimeRenderer:
    def build_screen_widget(
        self,
        screen: Screen,
        components: list[Component],
        on_component_clicked: Callable,
        assets_dir: Path | None = None,
    ) -> QWidget:
        root = QWidget()
        root.setAttribute(Qt.WA_StyledBackground, True)
        root.setFixedSize(int(screen.width), int(screen.height))

        bg_ok = False
        if (screen.background_type or "").lower() == "image" and screen.background_value and assets_dir:
            bp = resolve_asset_file(assets_dir, str(screen.background_value))
            if bp is not None:
                pm = load_pixmap_from_file(bp)
                if pm is not None and not pm.isNull():
                    letter = QColor("#ffffff")
                    fit = str(getattr(screen, "background_fit", None) or "contain")
                    try:
                        sp = int(getattr(screen, "background_scale_percent", None) or 100)
                    except (TypeError, ValueError):
                        sp = 100
                    scr = compose_screen_background_pixmap(
                        pm,
                        int(screen.width),
                        int(screen.height),
                        fit=fit,
                        scale_percent=sp,
                        letterbox=letter,
                    )
                    pal = root.palette()
                    pal.setBrush(QPalette.ColorRole.Window, QBrush(scr))
                    root.setPalette(pal)
                    root.setAutoFillBackground(True)
                    bg_ok = True
        if not bg_ok:
            if screen.background_type == "color" and screen.background_value:
                root.setStyleSheet(f"background-color: {screen.background_value};")
            else:
                root.setStyleSheet("background-color: #ffffff;")

        # Рендерим фон экрана в пиксмап — нужен для backdrop blur компонентов.
        # Создаём заранее, чтобы не включать сами компоненты в "подложку".
        bg_pixmap = self._render_background_pixmap(screen, assets_dir)

        # Кеш: {blur_radius -> размытый снимок ВСЕГО фона}.
        # Один раз размываем весь фон, виджет динамически кропает по своей pos().
        blur_full_cache: dict[int, QPixmap] = {}

        anim_entries: list[_AnimEntry] = []

        for c in sorted(components, key=lambda x: (int(x.z_index), int(x.id))):
            w = self._build_component_widget(c, parent=root, assets_dir=assets_dir)
            w.setVisible(bool(c.is_visible))
            w.setGeometry(int(c.x), int(c.y), int(c.width), int(c.height))
            w.setProperty("component_id", int(c.id))
            w.setAttribute(Qt.WA_AcceptTouchEvents, True)

            if isinstance(w, QPushButton):
                w.clicked.connect(lambda _=False, cid=int(c.id): on_component_clicked(cid))
            else:
                inner_btn = w.findChild(QPushButton)
                if inner_btn is not None:
                    inner_btn.clicked.connect(lambda _=False, cid=int(c.id): on_component_clicked(cid))
                else:
                    cid = int(c.id)

                    def _press(ev, _cid=cid, _w=w) -> None:
                        on_component_clicked(_cid)
                        QWidget.mousePressEvent(_w, ev)

                    w.mousePressEvent = _press  # type: ignore[method-assign]

            # Backdrop blur: передаём виджету весь размытый фон экрана.
            # Кроп по текущей позиции делается в paintEvent — поэтому при анимации
            # движения виджет всегда показывает правильный кусок фона под собой.
            if bool(c.is_visible):
                style = _safe_json(c.style_json)
                blur_r = int(style.get("blur_radius", 0))
                if blur_r > 0 and not bg_pixmap.isNull():
                    if blur_r not in blur_full_cache:
                        blur_full_cache[blur_r] = _blur_pixmap(bg_pixmap, float(blur_r))
                    blurred_full = blur_full_cache[blur_r]
                    if hasattr(w, "set_backdrop_source"):
                        w.set_backdrop_source(blurred_full)  # type: ignore[attr-defined]

                # Анимации появления
                anim_type = str(style.get("anim_type", "none")).lower().strip()
                if anim_type and anim_type != "none":
                    entry = _AnimEntry(
                        widget=w,
                        orig_geom=QRect(int(c.x), int(c.y), int(c.width), int(c.height)),
                        anim_type=anim_type,
                        delay_ms=max(0, int(style.get("anim_delay", 0))),
                        duration_ms=max(50, int(style.get("anim_duration", 500))),
                    )
                    _apply_initial_state(entry)
                    anim_entries.append(entry)

        scaled = RuntimeScaledScreen(int(screen.width), int(screen.height), root)
        scaled._entry_anim_ctrl = ScreenAnimController(anim_entries)  # type: ignore[attr-defined]
        return scaled

    def _render_background_pixmap(self, screen: Screen, assets_dir: Path | None) -> QPixmap:
        """Рендерит только фон экрана (без компонентов) в QPixmap для backdrop blur."""
        w, h = int(screen.width), int(screen.height)
        pm = QPixmap(w, h)

        # Базовый цвет
        if screen.background_type == "color" and screen.background_value:
            pm.fill(QColor(screen.background_value))
        else:
            pm.fill(QColor("#ffffff"))

        # Картинка поверх
        if (screen.background_type or "").lower() == "image" and screen.background_value and assets_dir:
            bp = resolve_asset_file(assets_dir, str(screen.background_value))
            if bp is not None:
                src = load_pixmap_from_file(bp)
                if src is not None and not src.isNull():
                    fit = str(getattr(screen, "background_fit", None) or "contain")
                    try:
                        sp = int(getattr(screen, "background_scale_percent", None) or 100)
                    except (TypeError, ValueError):
                        sp = 100
                    composed = compose_screen_background_pixmap(
                        src, w, h, fit=fit, scale_percent=sp, letterbox=QColor("#ffffff")
                    )
                    p = QPainter(pm)
                    p.drawPixmap(0, 0, composed)
                    p.end()
        return pm

    def _build_component_widget(self, c: Component, parent: QWidget, assets_dir: Path | None) -> QWidget:
        props = _safe_json(c.props_json)
        style = _safe_json(c.style_json)
        t = (c.type or "").lower()

        if t in ("text", "label"):
            return RuntimeMirrorTextWidget(
                parent,
                props,
                style,
                default_text=str(c.name or "Текст"),
            )

        if t in ("button", "nav.button"):
            bg_src = str(props.get("background_src", "") or "").strip()
            bg_pm: QPixmap | None = None
            if assets_dir and bg_src:
                bp = resolve_asset_file(assets_dir, bg_src)
                if bp is not None and bp.is_file():
                    bg_pm = load_pixmap_from_file(bp)
                    if bg_pm is not None and bg_pm.isNull():
                        bg_pm = None
            icon_pm: QPixmap | None = None
            icon_src = str(props.get("icon_src", "") or "").strip()
            if assets_dir and icon_src:
                ip = resolve_asset_file(assets_dir, icon_src)
                if ip is not None:
                    raw_icon = load_pixmap_from_file(ip)
                    if raw_icon is not None and not raw_icon.isNull():
                        icon_pm = raw_icon.scaled(
                            28,
                            28,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
            return RuntimeMirrorButton(
                parent,
                props,
                style,
                default_label=str(c.name or "Кнопка"),
                icon_pixmap=icon_pm,
                background_pixmap=bg_pm,
            )

        if t in ("shape.rectangle", "rectangle", "shape"):
            return RuntimeMirrorShapeRectWidget(parent, style)

        if t == "shape.ellipse":
            return RuntimeMirrorShapeEllipseWidget(parent, style)

        if t == "shape.line":
            return RuntimeMirrorShapeLineWidget(parent, style)

        if t == "image":
            pm: QPixmap | None = None
            src = str(props.get("src", "") or "").strip()
            if assets_dir and src:
                p = resolve_asset_file(assets_dir, src)
                if p is not None:
                    pm = load_pixmap_from_file(p)
                    if pm is not None and pm.isNull():
                        pm = None
            return RuntimeMirrorImageWidget(parent, style, pm)

        ph = QLabel(parent)
        ph.setText(str(c.type))
        ph.setAlignment(Qt.AlignCenter)
        ph.setStyleSheet("background-color: #fafafa; border: 1px dashed #999; color: #666; font-size: 14px;")
        return ph
