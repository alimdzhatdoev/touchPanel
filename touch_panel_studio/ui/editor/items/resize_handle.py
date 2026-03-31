from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsSceneMouseEvent


class HandleRole(str, Enum):
    tl = "tl"
    tr = "tr"
    bl = "bl"
    br = "br"
    tc = "tc"
    bc = "bc"
    cl = "cl"
    cr = "cr"


def _cursor_for_role(role: HandleRole) -> Qt.CursorShape:
    if role in (HandleRole.tc, HandleRole.bc):
        return Qt.CursorShape.SizeVerCursor
    if role in (HandleRole.cl, HandleRole.cr):
        return Qt.CursorShape.SizeHorCursor
    if role in (HandleRole.tl, HandleRole.br):
        return Qt.CursorShape.SizeFDiagCursor
    return Qt.CursorShape.SizeBDiagCursor


def _clamp_min_size(r: QRectF, role: HandleRole, min_w: float, min_h: float) -> QRectF:
    r = r.normalized()
    if r.width() < min_w:
        if role in (HandleRole.cl, HandleRole.tl, HandleRole.bl):
            r.setLeft(r.right() - min_w)
        else:
            r.setRight(r.left() + min_w)
    if r.height() < min_h:
        if role in (HandleRole.tc, HandleRole.tl, HandleRole.tr):
            r.setTop(r.bottom() - min_h)
        else:
            r.setBottom(r.top() + min_h)
    return r


class ResizeHandleItem(QGraphicsRectItem):
    def __init__(self, role: HandleRole, parent: QGraphicsRectItem) -> None:
        super().__init__(-6, -6, 12, 12, parent)
        self.role = role
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#1976d2"), 1))
        self.setZValue(10_000)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsRectItem.ItemIgnoresTransformations, True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(_cursor_for_role(role))
        self._start_scene: QPointF | None = None
        self._start_scene_rect: QRectF | None = None

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        parent = self.parentItem()
        if parent is None:
            event.ignore()
            return
        self._start_scene = event.scenePos()
        self._start_scene_rect = parent.mapRectToScene(parent.rect())
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._start_scene is None or self._start_scene_rect is None:
            return
        parent = self.parentItem()
        if parent is None:
            return
        delta = event.scenePos() - self._start_scene
        r = QRectF(self._start_scene_rect)
        role = self.role

        if role == HandleRole.br:
            r.setBottomRight(r.bottomRight() + delta)
        elif role == HandleRole.tl:
            r.setTopLeft(r.topLeft() + delta)
        elif role == HandleRole.tr:
            r.setTopRight(r.topRight() + delta)
        elif role == HandleRole.bl:
            r.setBottomLeft(r.bottomLeft() + delta)
        elif role == HandleRole.tc:
            r.setTop(r.top() + delta.y())
        elif role == HandleRole.bc:
            r.setBottom(r.bottom() + delta.y())
        elif role == HandleRole.cl:
            r.setLeft(r.left() + delta.x())
        elif role == HandleRole.cr:
            r.setRight(r.right() + delta.x())

        min_w, min_h = 20.0, 20.0
        r = _clamp_min_size(r, role, min_w, min_h)

        parent.setPos(r.topLeft())
        parent.setRect(QRectF(0, 0, r.width(), r.height()))
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self._start_scene = None
        self._start_scene_rect = None
        parent = self.parentItem()
        if parent is not None and hasattr(parent, "_notify_geometry_changed"):
            parent._notify_geometry_changed()  # type: ignore[attr-defined]
        event.accept()
