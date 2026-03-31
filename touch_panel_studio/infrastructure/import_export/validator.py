from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from touch_panel_studio.infrastructure.import_export.schemas import SchemaVersionFile, TemplateManifest


class TemplateValidationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TemplateValidator:
    def validate_manifest(self, manifest_path: Path) -> TemplateManifest:
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return TemplateManifest.model_validate(data)
        except (OSError, json.JSONDecodeError, ValidationError) as e:
            raise TemplateValidationError(f"Некорректный manifest.json: {e}") from e

    def validate_schema_version(self, schema_version_path: Path) -> SchemaVersionFile:
        try:
            data = json.loads(schema_version_path.read_text(encoding="utf-8"))
            return SchemaVersionFile.model_validate(data)
        except (OSError, json.JSONDecodeError, ValidationError) as e:
            raise TemplateValidationError(f"Некорректный schema_version.json: {e}") from e

