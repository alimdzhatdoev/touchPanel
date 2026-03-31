from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPalette, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from touch_panel_studio.db.models.component import Component
from touch_panel_studio.db.models.screen import Screen
from touch_panel_studio.infrastructure.storage.asset_paths import load_pixmap_from_file, resolve_asset_file
from touch_panel_studio.ui.common.background_compose import compose_screen_background_pixmap
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


class RuntimeRenderer:
    def build_screen_widget(
        self,
        screen: Screen,
        components: list[Component],
        on_component_clicked,
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

        return RuntimeScaledScreen(int(screen.width), int(screen.height), root)

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
