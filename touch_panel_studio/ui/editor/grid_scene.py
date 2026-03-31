from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsScene

from touch_panel_studio.infrastructure.storage.asset_paths import load_pixmap_from_file, resolve_asset_file
from touch_panel_studio.ui.common.background_compose import compose_screen_background_pixmap


def _letterbox_qcolor(bg_type: str, bg_value: str | None) -> QColor:
    if (bg_type or "").lower() == "color" and bg_value:
        try:
            c = QColor(bg_value)
            if c.isValid():
                return c
        except Exception:
            pass
    return QColor("#ffffff")


class GridScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self.grid_size = 20
        self._minor_pen = QPen(QColor("#efefef"))
        self._major_pen = QPen(QColor("#e0e0e0"))
        self._major_every = 5
        self._bg_type = "color"
        self._bg_value = "#ffffff"
        self._bg_pixmap: QPixmap | None = None
        self._bg_fit = "contain"
        self._bg_scale_percent = 100
        self._assets_dir: Path | None = None
        self._grid_opacity = 0.45
        self._rebuild_grid_pens()

    def set_grid_opacity(self, alpha: float) -> None:
        """0 = сетка скрыта, 1 = линии как в теме (с учётом альфа-канала базового цвета)."""
        self._grid_opacity = max(0.0, min(1.0, float(alpha)))
        self._rebuild_grid_pens()
        self.invalidate()

    def _rebuild_grid_pens(self) -> None:
        a = self._grid_opacity
        o = int(round(255 * a))
        self._minor_pen = QPen(QColor(239, 239, 239, o))
        self._major_pen = QPen(QColor(224, 224, 224, o))

    def set_screen_background(
        self,
        bg_type: str,
        bg_value: str | None,
        assets_dir: Path | None,
        *,
        background_fit: str = "contain",
        background_scale_percent: int = 100,
    ) -> None:
        self._bg_type = (bg_type or "color").lower()
        self._bg_value = (bg_value or "").strip()
        self._assets_dir = assets_dir
        self._bg_fit = (background_fit or "contain").lower().strip()
        try:
            self._bg_scale_percent = max(50, min(300, int(background_scale_percent)))
        except (TypeError, ValueError):
            self._bg_scale_percent = 100
        self._bg_pixmap = None
        if self._bg_type == "image" and assets_dir and self._bg_value:
            p = resolve_asset_file(assets_dir, self._bg_value)
            if p is not None:
                pm = load_pixmap_from_file(p)
                if pm is not None and not pm.isNull():
                    self._bg_pixmap = pm
        self.invalidate()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        sr = self.sceneRect()
        if not sr.isValid() or sr.width() <= 0 or sr.height() <= 0:
            return

        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():
            letter = _letterbox_qcolor(self._bg_type, self._bg_value)
            composed = compose_screen_background_pixmap(
                self._bg_pixmap,
                int(sr.width()),
                int(sr.height()),
                fit=self._bg_fit,
                scale_percent=self._bg_scale_percent,
                letterbox=letter,
            )
            painter.drawPixmap(sr.toRect(), composed, composed.rect())
        else:
            c = QColor("#ffffff")
            if self._bg_type == "color" and self._bg_value:
                try:
                    c = QColor(self._bg_value)
                except Exception:
                    pass
            painter.fillRect(sr, c)

        if self._grid_opacity <= 0.001:
            return

        gs = self.grid_size
        if gs <= 1:
            return

        left = int(rect.left()) - (int(rect.left()) % gs)
        top = int(rect.top()) - (int(rect.top()) % gs)

        lines_minor: list[tuple[float, float, float, float]] = []
        lines_major: list[tuple[float, float, float, float]] = []

        x = float(left)
        while x < rect.right():
            pen_lines = lines_major if ((int(x) // gs) % self._major_every == 0) else lines_minor
            pen_lines.append((x, rect.top(), x, rect.bottom()))
            x += gs

        y = float(top)
        while y < rect.bottom():
            pen_lines = lines_major if ((int(y) // gs) % self._major_every == 0) else lines_minor
            pen_lines.append((rect.left(), y, rect.right(), y))
            y += gs

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.setPen(self._minor_pen)
        for x1, y1, x2, y2 in lines_minor:
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.setPen(self._major_pen)
        for x1, y1, x2, y2 in lines_major:
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.restore()
