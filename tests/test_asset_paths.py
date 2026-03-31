from __future__ import annotations

import tempfile
from pathlib import Path

from touch_panel_studio.infrastructure.storage.asset_paths import resolve_asset_file


def test_resolve_asset_file_spaces_and_parens() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "assets"
        root.mkdir()
        weird = root / "file-2_00x (1).png"
        weird.write_bytes(b"x")
        assert resolve_asset_file(root, "file-2_00x (1).png") == weird.resolve()
        assert resolve_asset_file(root, r"file-2_00x (1).png") == weird.resolve()
