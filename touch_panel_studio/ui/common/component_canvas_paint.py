"""Общая отрисовка компонентов канваса — та же логика, что в редакторе, для совпадения с runtime."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene
from touch_panel_studio.ui.common.text_typography import paint_styled_text_block


def blur_pixmap(pixmap: QPixmap, radius: float) -> QPixmap:
    """Размывает пиксмап через временную QGraphicsScene (стандартная техника Qt)."""
    if radius <= 0 or pixmap.isNull():
        return pixmap
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(pixmap)
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(float(radius))
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    result = QPixmap(pixmap.size())
    result.fill(Qt.GlobalColor.transparent)
    p = QPainter(result)
    scene.render(p, QRectF(result.rect()), QRectF(item.boundingRect()))
    p.end()
    scene.deleteLater()
    return result


def stroke_pen_from_style(style: dict) -> QPen:
    sw = int(style.get("stroke_width", 1))
    sw = max(0, sw)
    if sw == 0:
        return QPen(Qt.PenStyle.NoPen)
    raw = style.get("stroke", None)
    if raw is None:
        return QPen(QColor("#333333"), float(sw))
    s = str(raw).strip().lower()
    if s in ("transparent", "none", ""):
        return QPen(Qt.PenStyle.NoPen)
    c = QColor(s)
    if not c.isValid():
        return QPen(Qt.PenStyle.NoPen)
    return QPen(c, float(sw))


def fill_brush_from_style(style: dict) -> QBrush:
    raw = style.get("fill", None)
    if raw is None:
        return QBrush(QColor("#ffffff"))
    fs = str(raw).strip().lower()
    if fs in ("transparent", "none", ""):
        return QBrush(Qt.BrushStyle.NoBrush)
    c = QColor(fs)
    if not c.isValid():
        return QBrush(Qt.BrushStyle.NoBrush)
    return QBrush(c)


def paint_rounded_rect(
    painter: QPainter,
    r: QRectF,
    style: dict,
    *,
    fill: bool,
    stroke: bool,
) -> None:
    radius = float(style.get("radius", 0))
    radius = max(0.0, min(radius, min(r.width(), r.height()) / 2.0))
    path = QPainterPath()
    path.addRoundedRect(r, radius, radius)
    if fill:
        painter.setBrush(fill_brush_from_style(style))
    else:
        painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(stroke_pen_from_style(style) if stroke else QPen(Qt.PenStyle.NoPen))
    painter.drawPath(path)


def paint_shape_ellipse(painter: QPainter, r: QRectF, style: dict) -> None:
    painter.setBrush(fill_brush_from_style(style))
    painter.setPen(stroke_pen_from_style(style))
    painter.drawEllipse(r)


def paint_shape_line(painter: QPainter, r: QRectF, style: dict) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(stroke_pen_from_style(style))
    y = r.center().y()
    painter.drawLine(r.left(), y, r.right(), y)


def paint_text_component(painter: QPainter, r: QRectF, text: str, style: dict) -> None:
    paint_styled_text_block(
        painter,
        r,
        text,
        style=style,
        default_size=24,
        default_family="Segoe UI",
    )


def paint_button_component(
    painter: QPainter,
    r: QRectF,
    *,
    label: str,
    style: dict,
    icon_pixmap: QPixmap | None,
    background_pixmap: QPixmap | None,
) -> None:
    radius = float(style.get("radius", 0))
    radius = max(0.0, min(radius, min(r.width(), r.height()) / 2.0))
    clip = QPainterPath()
    clip.addRoundedRect(r, radius, radius)

    if background_pixmap is not None and not background_pixmap.isNull():
        painter.save()
        painter.setClipPath(clip)
        pm = background_pixmap
        rw, rh = float(r.width()), float(r.height())
        iw, ih = float(pm.width()), float(pm.height())
        if iw > 0 and ih > 0:
            scale = max(rw / iw, rh / ih)
            tw = max(1, int(round(iw * scale)))
            th = max(1, int(round(ih * scale)))
            scaled = pm.scaled(
                tw,
                th,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            sw, sh = float(scaled.width()), float(scaled.height())
            x = r.left() + (rw - sw) / 2.0
            y = r.top() + (rh - sh) / 2.0
            painter.drawPixmap(QRectF(x, y, sw, sh).toRect(), scaled, scaled.rect())
        painter.restore()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(stroke_pen_from_style(style))
        painter.drawPath(clip)
    else:
        paint_rounded_rect(painter, r, style, fill=True, stroke=True)

    text_rect = QRectF(r)
    if icon_pixmap is not None and not icon_pixmap.isNull():
        pad = 8.0
        iw = float(icon_pixmap.width())
        ih = float(icon_pixmap.height())
        iy = r.top() + (r.height() - ih) / 2.0
        target = QRectF(r.left() + pad, iy, iw, ih).toRect()
        painter.drawPixmap(target, icon_pixmap)
        text_rect.setLeft(r.left() + pad + iw + pad)
    paint_styled_text_block(
        painter,
        text_rect,
        label,
        style=style,
        default_size=20,
        default_family="Segoe UI",
        valign_default="center",
    )


def paint_image_component(
    painter: QPainter,
    r: QRectF,
    *,
    style: dict,
    pixmap: QPixmap | None,
    missing_caption: str = "Изображение\n(укажите файл или «Загрузить…»)",
) -> None:
    if "fill" in style:
        fb = fill_brush_from_style(style)
        if fb.style() != Qt.BrushStyle.NoBrush:
            painter.fillRect(r, fb)
    if pixmap is not None and not pixmap.isNull():
        scaled = pixmap.scaled(
            int(r.width()),
            int(r.height()),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = r.left() + (r.width() - scaled.width()) / 2.0
        y = r.top() + (r.height() - scaled.height()) / 2.0
        tr = QRectF(x, y, float(scaled.width()), float(scaled.height())).toRect()
        painter.drawPixmap(tr, scaled, scaled.rect())
        sp = stroke_pen_from_style(style)
        if sp.style() != Qt.PenStyle.NoPen:
            painter.setPen(sp)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r)
    else:
        painter.fillRect(r, QColor("#eeeeee"))
        painter.setPen(QPen(QColor("#999999"), 1, Qt.PenStyle.DashLine))
        painter.drawRect(r)
        painter.setPen(QColor("#666666"))
        painter.drawText(r, int(Qt.AlignmentFlag.AlignCenter), missing_caption)
