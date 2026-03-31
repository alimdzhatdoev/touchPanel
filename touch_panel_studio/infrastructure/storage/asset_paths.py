"""Разрешение путей к файлам в каталоге assets (Windows, пробелы, скобки в имени)."""

from __future__ import annotations

from pathlib import Path


def resolve_asset_file(assets_dir: Path | None, relative: str | None) -> Path | None:
    """
    Возвращает существующий файл внутри assets_dir по относительному пути из БД.
    Пробует прямой путь, затем только имя файла в корне assets, затем rglob по имени.
    """
    if not assets_dir or not relative:
        return None
    raw = str(relative).strip().strip("\ufeff").strip('"').strip("'")
    if not raw:
        return None
    raw = raw.replace("\\", "/").lstrip("/")
    while raw.startswith("./"):
        raw = raw[2:]

    root = assets_dir.resolve()

    def _under_assets(p: Path) -> bool:
        try:
            p.resolve().relative_to(root)
            return True
        except ValueError:
            return False

    try:
        p = (root / raw).resolve()
        if p.is_file() and _under_assets(p):
            return p
    except OSError:
        pass

    name = Path(raw).name
    if name:
        try:
            p2 = (root / name).resolve()
            if p2.is_file() and _under_assets(p2):
                return p2
        except OSError:
            pass
        try:
            for cand in root.rglob(name):
                if cand.is_file() and _under_assets(cand):
                    return cand.resolve()
        except OSError:
            pass
    return None


def load_pixmap_from_file(path: Path):
    """QPixmap из файла; SVG через QSvgRenderer; иначе QImage (PNG с профилями и т.д.)."""
    from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

    suf = path.suffix.lower()
    if suf == ".svg":
        try:
            from PySide6.QtSvg import QSvgRenderer

            r = QSvgRenderer(str(path))
            if r.isValid():
                sz = r.defaultSize()
                w, h = max(1, sz.width()), max(1, sz.height())
                pm = QPixmap(w, h)
                pm.fill(QColor(0, 0, 0, 0))
                p = QPainter(pm)
                r.render(p)
                p.end()
                if not pm.isNull():
                    return pm
        except Exception:
            pass

    pm = QPixmap(str(path))
    if not pm.isNull():
        return pm
    img = QImage(str(path))
    if img.isNull():
        return None
    return QPixmap.fromImage(img)
