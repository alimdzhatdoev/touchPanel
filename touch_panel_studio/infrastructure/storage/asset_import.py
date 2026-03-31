"""Копирование выбранных файлов в каталог assets проекта."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path


def import_file_into_assets(assets_dir: Path, source: Path) -> str:
    """
    Копирует файл в assets_dir, при совпадении имени добавляет суффикс.
    Возвращает относительный путь с прямыми слэшами (для JSON/БД).
    """
    assets_dir = assets_dir.resolve()
    assets_dir.mkdir(parents=True, exist_ok=True)
    src = source.resolve()
    if not src.is_file():
        raise FileNotFoundError(str(src))

    stem = src.stem
    suffix = src.suffix.lower() or ".bin"
    dest = assets_dir / f"{stem}{suffix}"
    if dest.exists():
        dest = assets_dir / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    shutil.copy2(src, dest)
    rel = dest.relative_to(assets_dir)
    return str(rel).replace("\\", "/")
