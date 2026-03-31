from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SchemaVersion = Literal[1]


class SchemaVersionFile(BaseModel):
    schema_version: SchemaVersion = 1


class TemplateManifest(BaseModel):
    schema_version: SchemaVersion = 1
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    app: str = "touch_panel_studio"

    kind: Literal["project", "template", "screens"] = "project"
    name: str
    code: str
    version: str = "1.0.0"

    counts: dict[str, int] = Field(default_factory=dict)
    notes: str | None = None


class ProjectJson(BaseModel):
    name: str
    code: str
    description: str | None = None
    version: str = "1.0.0"


class ScreenRow(BaseModel):
    id: int
    project_id: int
    name: str
    slug: str
    screen_type: str
    width: int
    height: int
    sort_order: int
    is_home: bool
    is_published: bool
    background_type: str
    background_value: str | None = None
    background_fit: str = "contain"
    background_scale_percent: int = 100


class ComponentRow(BaseModel):
    id: int
    screen_id: int
    type: str
    name: str | None = None
    x: int
    y: int
    width: int
    height: int
    z_index: int
    rotation: int
    is_visible: bool
    props_json: str
    style_json: str
    bindings_json: str


class ScreenActionRow(BaseModel):
    id: int
    source_screen_id: int
    source_component_id: int | None = None
    trigger_type: str
    action_type: str
    target_screen_id: int | None = None
    payload_json: str


class AssetRow(BaseModel):
    id: int
    project_id: int
    asset_type: str
    file_name: str
    original_name: str | None = None
    relative_path: str
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None


class DataBundle(BaseModel):
    screens: list[ScreenRow] = Field(default_factory=list)
    components: list[ComponentRow] = Field(default_factory=list)
    screen_actions: list[ScreenActionRow] = Field(default_factory=list)
    assets: list[AssetRow] = Field(default_factory=list)

