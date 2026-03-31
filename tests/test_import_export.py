from __future__ import annotations

import json
import tempfile
from pathlib import Path

from touch_panel_studio.infrastructure.import_export.schemas import SchemaVersionFile, TemplateManifest
from touch_panel_studio.infrastructure.import_export.validator import TemplateValidator


def test_template_manifest_roundtrip() -> None:
    m = TemplateManifest(name="Test", code="test-proj", version="1.0.0", kind="project")
    data = json.loads(m.model_dump_json())
    m2 = TemplateManifest.model_validate(data)
    assert m2.code == "test-proj"
    assert m2.schema_version == 1


def test_validator_reads_manifest(tmp_path: Path) -> None:
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "X",
                "code": "x-code",
                "version": "1.0.0",
                "kind": "project",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    v = TemplateValidator()
    m = v.validate_manifest(p)
    assert m.code == "x-code"


def test_schema_version_file() -> None:
    s = SchemaVersionFile(schema_version=1)
    assert s.schema_version == 1
