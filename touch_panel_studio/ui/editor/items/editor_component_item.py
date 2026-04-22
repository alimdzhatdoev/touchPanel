from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QStyleOptionGraphicsItem, QWidget

from touch_panel_studio.db.models.component import Component
from touch_panel_studio.infrastructure.storage.asset_paths import load_pixmap_from_file, resolve_asset_file
from touch_panel_studio.ui.common.component_canvas_paint import (
    paint_button_component,
    paint_image_component,
    paint_rounded_rect,
    paint_shape_ellipse,
    paint_shape_line,
    paint_text_component,
)
from touch_panel_studio.ui.editor.items.resize_handle import HandleRole, ResizeHandleItem


def _safe_json(s: str) -> dict:
    try:
        v = json.loads(s or "{}")
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


class EditorComponentItem(QGraphicsRectItem):
    """Элемент сцены: отрисовка по типу компонента и данным props/style."""

    def __init__(
        self,
        component_id: int,
        rect: QRectF,
        comp_type: str,
        props_json: str,
        style_json: str,
        assets_dir: Path | None = None,
    ) -> None:
        super().__init__(rect)
        self.component_id = component_id
        self._assets_dir = assets_dir
        self._type = (comp_type or "").lower()
        self._props = _safe_json(props_json)
        self._style = _safe_json(style_json)
        self._pixmap: QPixmap | None = None
        self._icon_pixmap: QPixmap | None = None
        self._button_bg_pixmap: QPixmap | None = None

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self._pen_normal = QPen(QColor("#333333"), 1)
        self._pen_selected = QPen(QColor("#1976d2"), 2)
        self.setPen(self._pen_normal)

        self._handles = {
            HandleRole.tl: ResizeHandleItem(HandleRole.tl, self),
            HandleRole.tr: ResizeHandleItem(HandleRole.tr, self),
            HandleRole.bl: ResizeHandleItem(HandleRole.bl, self),
            HandleRole.br: ResizeHandleItem(HandleRole.br, self),
            HandleRole.tc: ResizeHandleItem(HandleRole.tc, self),
            HandleRole.bc: ResizeHandleItem(HandleRole.bc, self),
            HandleRole.cl: ResizeHandleItem(HandleRole.cl, self),
            HandleRole.cr: ResizeHandleItem(HandleRole.cr, self),
        }
        for h in self._handles.values():
            h.setVisible(False)
        self._sync_handles()
        self._load_pixmap_if_needed()

    @classmethod
    def from_component(cls, c: Component, assets_dir: Path | None) -> EditorComponentItem:
        r = QRectF(0, 0, float(c.width), float(c.height))
        it = cls(
            component_id=int(c.id),
            rect=r,
            comp_type=str(c.type),
            props_json=c.props_json,
            style_json=c.style_json,
            assets_dir=assets_dir,
        )
        it.setPos(float(c.x), float(c.y))
        it.setZValue(float(c.z_index))
        it.setVisible(bool(c.is_visible))
        return it

    def apply_component(self, c: Component) -> None:
        self._type = (c.type or "").lower()
        self._props = _safe_json(c.props_json)
        self._style = _safe_json(c.style_json)
        self._load_pixmap_if_needed()
        self.update()

    def set_assets_dir(self, assets_dir: Path | None) -> None:
        self._assets_dir = assets_dir.resolve() if assets_dir else None
        self._load_pixmap_if_needed()
        self.update()

    def _load_pixmap_if_needed(self) -> None:
        self._pixmap = None
        self._icon_pixmap = None
        self._button_bg_pixmap = None
        if self._type == "image":
            src = str(self._props.get("src", "") or "").strip()
            if src and self._assets_dir:
                p = resolve_asset_file(self._assets_dir, src)
                if p is not None:
                    pm = load_pixmap_from_file(p)
                    if pm is not None and not pm.isNull():
                        self._pixmap = pm
        elif self._type in ("button", "nav.button"):
            bg = str(self._props.get("background_src", "") or "").strip()
            if bg and self._assets_dir:
                p = resolve_asset_file(self._assets_dir, bg)
                if p is not None:
                    pm = load_pixmap_from_file(p)
                    if pm is not None and not pm.isNull():
                        self._button_bg_pixmap = pm
            src = str(self._props.get("icon_src", "") or "").strip()
            if src and self._assets_dir:
                p = resolve_asset_file(self._assets_dir, src)
                if p is not None:
                    pm = load_pixmap_from_file(p)
                    if pm is not None and not pm.isNull():
                        self._icon_pixmap = pm.scaled(
                            28,
                            28,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            selected = bool(value)
            self.setPen(self._pen_selected if selected else self._pen_normal)
            for h in self._handles.values():
                h.setVisible(selected)
            self._sync_handles()
        elif change in (QGraphicsItem.ItemPositionHasChanged, QGraphicsItem.ItemTransformHasChanged):
            self._sync_handles()
        return super().itemChange(change, value)

    def setRect(self, rect: QRectF) -> None:  # type: ignore[override]
        super().setRect(rect)
        self._sync_handles()

    def _sync_handles(self) -> None:
        r = self.rect()
        cx = r.center().x()
        cy = r.center().y()
        self._handles[HandleRole.tl].setPos(r.topLeft())
        self._handles[HandleRole.tr].setPos(r.topRight())
        self._handles[HandleRole.bl].setPos(r.bottomLeft())
        self._handles[HandleRole.br].setPos(r.bottomRight())
        self._handles[HandleRole.tc].setPos(QPointF(cx, r.top()))
        self._handles[HandleRole.bc].setPos(QPointF(cx, r.bottom()))
        self._handles[HandleRole.cl].setPos(QPointF(r.left(), cy))
        self._handles[HandleRole.cr].setPos(QPointF(r.right(), cy))

    def geometry_int(self) -> tuple[int, int, int, int]:
        pos: QPointF = self.pos()
        r = self.rect()
        return int(pos.x()), int(pos.y()), int(r.width()), int(r.height())

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        super().mouseReleaseEvent(event)
        self._notify_geometry_changed()

    def _notify_geometry_changed(self) -> None:
        scene = self.scene()
        if scene and hasattr(scene, "views") and scene.views():
            view = scene.views()[0]
            parent = view.parent()
            while parent is not None:
                if hasattr(parent, "notify_item_geometry_changed"):
                    x, y, w, h = self.geometry_int()
                    parent.notify_item_geometry_changed(self.component_id, x, y, w, h)  # type: ignore[attr-defined]
                    break
                parent = parent.parent()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        del option, widget
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        r = self.rect()
        t = self._type

        # Backdrop blur preview: crop blurred background at item's scene position
        blur_r = int(self._style.get("blur_radius", 0))
        if blur_r > 0:
            scene = self.scene()
            if hasattr(scene, "get_blurred_background"):
                blurred = scene.get_blurred_background(blur_r)
                if blurred is not None and not blurred.isNull():
                    sp = self.scenePos()
                    crop = blurred.copy(int(sp.x()), int(sp.y()), int(r.width()), int(r.height()))
                    radius = float(self._style.get("radius", 0))
                    radius = max(0.0, min(radius, min(r.width(), r.height()) / 2.0))
                    painter.save()
                    painter.setOpacity(1.0)
                    if radius > 0:
                        clip_path = QPainterPath()
                        clip_path.addRoundedRect(r, radius, radius)
                        painter.setClipPath(clip_path)
                    painter.drawPixmap(r.toRect(), crop, crop.rect())
                    painter.restore()

        op = float(self._style.get("opacity", 1.0))
        if op < 0:
            op = 0.0
        if op > 1:
            op = 1.0
        painter.setOpacity(op)

        if t in ("shape.rectangle", "shape", "rectangle"):
            paint_rounded_rect(painter, r, self._style, fill=True, stroke=True)
        elif t == "shape.ellipse":
            paint_shape_ellipse(painter, r, self._style)
        elif t == "shape.line":
            paint_shape_line(painter, r, self._style)
        elif t in ("text", "label"):
            paint_text_component(painter, r, str(self._props.get("text", "Текст")), self._style)
        elif t in ("button", "nav.button"):
            paint_button_component(
                painter,
                r,
                label=str(self._props.get("text", "Кнопка")),
                style=self._style,
                icon_pixmap=self._icon_pixmap,
                background_pixmap=self._button_bg_pixmap,
            )
        elif t == "image":
            paint_image_component(painter, r, style=self._style, pixmap=self._pixmap)
        else:
            painter.fillRect(r, QColor("#f5f5f5"))
            painter.setPen(QPen(QColor("#999999"), 1, Qt.DashLine))
            painter.drawRect(r)
            painter.setPen(QColor("#666666"))
            painter.drawText(r, Qt.AlignCenter, t or "?")

        if self.isSelected():
            sel = QPen(QColor("#1976d2"), 2, Qt.DashLine)
            painter.setOpacity(1.0)
            painter.setPen(sel)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(r.adjusted(-1, -1, 1, 1))


# Обратная совместимость импорта
EditorRectItem = EditorComponentItem
