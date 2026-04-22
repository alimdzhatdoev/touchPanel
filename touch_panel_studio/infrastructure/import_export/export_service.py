from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from touch_panel_studio.db.models.asset import Asset
from touch_panel_studio.db.models.component import Component
from touch_panel_studio.db.models.project import Project
from touch_panel_studio.db.models.screen import Screen
from touch_panel_studio.db.models.screen_action import ScreenAction
from touch_panel_studio.infrastructure.import_export.schemas import (
    DataBundle,
    SchemaVersionFile,
    TemplateManifest,
)
from touch_panel_studio.infrastructure.storage.project_storage import ProjectHandle


@dataclass(frozen=True, slots=True)
class ProjectExportService:
    def export_full_project(self, handle: ProjectHandle, out_file: Path) -> Path:
        out_file = out_file.with_suffix(".tpanel")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        sf = handle.open_db()
        with sf.session() as s:
            project = s.scalar(select(Project).limit(1))
            if project is None:
                project_name = handle.meta.name
                project_code = handle.meta.code
                project_version = handle.meta.version
            else:
                project_name = str(project.name)
                project_code = str(project.code)
                project_version = str(project.version)

            screens = list(s.scalars(select(Screen)))
            components = list(s.scalars(select(Component)))
            actions = list(s.scalars(select(ScreenAction)))
            assets = list(s.scalars(select(Asset)))

        bundle = DataBundle(
            screens=[
                {
                    "id": int(x.id),
                    "project_id": int(x.project_id),
                    "name": x.name,
                    "slug": x.slug,
                    "screen_type": x.screen_type,
                    "width": int(x.width),
                    "height": int(x.height),
                    "sort_order": int(x.sort_order),
                    "is_home": bool(x.is_home),
                    "is_published": bool(x.is_published),
                    "background_type": x.background_type,
                    "background_value": x.background_value,
                    "background_fit": getattr(x, "background_fit", None) or "contain",
                    "background_scale_percent": int(getattr(x, "background_scale_percent", None) or 100),
                    "transition_json": getattr(x, "transition_json", None) or "{}",
                }
                for x in screens
            ],
            components=[
                {
                    "id": int(x.id),
                    "screen_id": int(x.screen_id),
                    "type": x.type,
                    "name": x.name,
                    "x": int(x.x),
                    "y": int(x.y),
                    "width": int(x.width),
                    "height": int(x.height),
                    "z_index": int(x.z_index),
                    "rotation": int(x.rotation),
                    "is_visible": bool(x.is_visible),
                    "props_json": x.props_json,
                    "style_json": x.style_json,
                    "bindings_json": x.bindings_json,
                }
                for x in components
            ],
            screen_actions=[
                {
                    "id": int(x.id),
                    "source_screen_id": int(x.source_screen_id),
                    "source_component_id": (int(x.source_component_id) if x.source_component_id is not None else None),
                    "trigger_type": x.trigger_type,
                    "action_type": x.action_type,
                    "target_screen_id": (int(x.target_screen_id) if x.target_screen_id is not None else None),
                    "payload_json": x.payload_json,
                }
                for x in actions
            ],
            assets=[
                {
                    "id": int(x.id),
                    "project_id": int(x.project_id),
                    "asset_type": x.asset_type,
                    "file_name": x.file_name,
                    "original_name": x.original_name,
                    "relative_path": x.relative_path,
                    "mime_type": x.mime_type,
                    "size_bytes": x.size_bytes,
                    "checksum": x.checksum,
                }
                for x in assets
            ],
        )

        manifest = TemplateManifest(
            schema_version=1,
            exported_at=datetime.utcnow(),
            kind="project",
            name=project_name,
            code=project_code,
            version=project_version,
            counts={
                "screens": len(bundle.screens),
                "components": len(bundle.components),
                "screen_actions": len(bundle.screen_actions),
                "assets": len(bundle.assets),
            },
        )

        schema_file = SchemaVersionFile(schema_version=1)

        with tempfile.TemporaryDirectory(prefix="tpanel_export_") as td:
            root = Path(td)
            data_dir = root / "data"
            assets_dir = root / "assets"
            data_dir.mkdir(parents=True, exist_ok=True)
            assets_dir.mkdir(parents=True, exist_ok=True)

            (root / "manifest.json").write_text(manifest.model_dump_json(indent=2, by_alias=True), encoding="utf-8")
            (root / "schema_version.json").write_text(schema_file.model_dump_json(indent=2), encoding="utf-8")
            (root / "project.json").write_text(
                json.dumps(
                    {
                        "name": project_name,
                        "code": project_code,
                        "description": handle.meta.description,
                        "version": project_version,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            (data_dir / "screens.json").write_text(
                json.dumps([x.model_dump() for x in bundle.screens], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (data_dir / "components.json").write_text(
                json.dumps([x.model_dump() for x in bundle.components], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (data_dir / "screen_actions.json").write_text(
                json.dumps([x.model_dump() for x in bundle.screen_actions], ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (data_dir / "assets.json").write_text(
                json.dumps([x.model_dump() for x in bundle.assets], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            # copy assets folder as-is
            if handle.assets_dir.exists():
                for p in handle.assets_dir.rglob("*"):
                    if p.is_dir():
                        continue
                    rel = p.relative_to(handle.assets_dir)
                    target = assets_dir / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, target)

            tmp_zip = root / "out.tpanel"
            with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for p in root.rglob("*"):
                    if p == tmp_zip or p.is_dir():
                        continue
                    zf.write(p, p.relative_to(root).as_posix())

            tmp_zip.replace(out_file)

        return out_file

