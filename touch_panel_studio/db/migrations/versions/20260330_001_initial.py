"""initial schema

Revision ID: 20260330_001
Revises: None
Create Date: 2026-03-30

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260330_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_code", "projects", ["code"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("admin", "editor", "viewer", "service", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "screens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("screen_type", sa.String(length=50), nullable=False, server_default="default"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1920"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="1080"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_home", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("background_type", sa.String(length=30), nullable=False, server_default="color"),
        sa.Column("background_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_screens_project_id", "screens", ["project_id"], unique=False)
    op.create_index("ix_screens_slug", "screens", ["slug"], unique=False)

    op.create_table(
        "components",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("screen_id", sa.Integer(), sa.ForeignKey("screens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("x", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("y", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="40"),
        sa.Column("z_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rotation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("props_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("style_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("bindings_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_components_screen_id", "components", ["screen_id"], unique=False)

    op.create_table(
        "screen_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_screen_id", sa.Integer(), sa.ForeignKey("screens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_component_id", sa.Integer(), sa.ForeignKey("components.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trigger_type", sa.Text(), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("target_screen_id", sa.Integer(), sa.ForeignKey("screens.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_screen_actions_source_screen_id", "screen_actions", ["source_screen_id"], unique=False)
    op.create_index("ix_screen_actions_source_component_id", "screen_actions", ["source_component_id"], unique=False)
    op.create_index("ix_screen_actions_target_screen_id", "screen_actions", ["target_screen_id"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=True),
        sa.Column("relative_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=200), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assets_project_id", "assets", ["project_id"], unique=False)

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0.0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manifest_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_templates_code", "templates", ["code"], unique=True)

    op.create_table(
        "revisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_revisions_project_id", "revisions", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_revisions_project_id", table_name="revisions")
    op.drop_table("revisions")

    op.drop_index("ix_templates_code", table_name="templates")
    op.drop_table("templates")

    op.drop_index("ix_assets_project_id", table_name="assets")
    op.drop_table("assets")

    op.drop_index("ix_screen_actions_target_screen_id", table_name="screen_actions")
    op.drop_index("ix_screen_actions_source_component_id", table_name="screen_actions")
    op.drop_index("ix_screen_actions_source_screen_id", table_name="screen_actions")
    op.drop_table("screen_actions")

    op.drop_index("ix_components_screen_id", table_name="components")
    op.drop_table("components")

    op.drop_index("ix_screens_slug", table_name="screens")
    op.drop_index("ix_screens_project_id", table_name="screens")
    op.drop_table("screens")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_projects_code", table_name="projects")
    op.drop_table("projects")

    op.execute("DROP TYPE IF EXISTS user_role")

