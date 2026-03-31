from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from touch_panel_studio.infrastructure.import_export.schemas import SchemaVersionFile


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VersionMigrator:
    def migrate_to_current(self, extracted_dir: Path, schema: SchemaVersionFile) -> SchemaVersionFile:
        # MVP: schema_version=1 is current, nothing to do.
        if schema.schema_version != 1:
            raise MigrationError(f"Неизвестная версия схемы: {schema.schema_version}")
        return schema

