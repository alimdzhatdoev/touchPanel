"""Сборка фона экрана из картинки с сохранением пропорций (редактор и runtime)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap


def compose_screen_background_pixmap(
    pm: QPixmap,
    width: int,
    height: int,
    *,
    fit: str,
    scale_percent: int,
    letterbox: QColor,
) -> QPixmap:
    """
    fit: contain | cover | stretch
    scale_percent: 50–300, множитель к вычисленному размеру (от центра).
    """
    w, h = max(1, int(width)), max(1, int(height))
    out = QPixmap(w, h)
    out.fill(letterbox)

    if pm.isNull():
        return out

    iw, ih = pm.width(), pm.height()
    if iw < 1 or ih < 1:
        return out

    fit_l = (fit or "contain").lower().strip()
    try:
        sp = int(scale_percent)
    except (TypeError, ValueError):
        sp = 100
    sp = max(50, min(300, sp))
    k = sp / 100.0

    p = QPainter(out)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    if fit_l == "stretch":
        scaled = pm.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        p.drawPixmap(0, 0, scaled)
        p.end()
        return out

    if fit_l == "cover":
        # Заполнить экран, обрезать лишнее
        s = max(w / iw, h / ih) * k
        tw = int(round(iw * s))
        th = int(round(ih * s))
        scaled = pm.scaled(tw, th, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        sw, sh = scaled.width(), scaled.height()
        x0 = (sw - w) // 2
        y0 = (sh - h) // 2
        p.drawPixmap(0, 0, w, h, scaled, x0, y0, w, h)
        p.end()
        return out

    # contain: вписать в экран, поля залить letterbox
    s = min(w / iw, h / ih) * k
    tw = int(round(iw * s))
    th = int(round(ih * s))
    scaled = pm.scaled(tw, th, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    sw, sh = scaled.width(), scaled.height()
    x = (w - sw) // 2
    y = (h - sh) // 2
    p.drawPixmap(x, y, scaled)
    p.end()
    return out
