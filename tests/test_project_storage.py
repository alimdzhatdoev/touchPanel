from __future__ import annotations

import tempfile
from pathlib import Path

from touch_panel_studio.infrastructure.storage.project_storage import ProjectStorage


def test_create_and_open_project() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "projects"
        ps = ProjectStorage(projects_root=root)
        h = ps.create_project(name="P1", code="proj-test-1", description=None)
        assert h.db_file.exists()
        assert h.assets_dir.is_dir()
        h2 = ps.open_project("proj-test-1")
        assert h2.meta.code == "proj-test-1"
