from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from touch_panel_studio.db.base import Base


class ScreenAction(Base):
    __tablename__ = "screen_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id", ondelete="CASCADE"), index=True, nullable=False)
    source_component_id: Mapped[int | None] = mapped_column(
        ForeignKey("components.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    trigger_type: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_screen_id: Mapped[int | None] = mapped_column(
        ForeignKey("screens.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

