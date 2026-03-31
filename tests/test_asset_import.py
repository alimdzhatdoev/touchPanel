from __future__ import annotations

import tempfile
from pathlib import Path

from touch_panel_studio.infrastructure.storage.asset_import import import_file_into_assets


def test_import_file_into_assets_copies_and_returns_relative() -> None:
    with tempfile.TemporaryDirectory() as td:
        assets = Path(td) / "assets"
        src = Path(td) / "a.png"
        src.write_bytes(b"x")
        rel = import_file_into_assets(assets, src)
        assert rel == "a.png"
        assert (assets / "a.png").is_file()
