from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from touch_panel_studio.db.base import Base


class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id", ondelete="CASCADE"), index=True, nullable=False)

    type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)

    x: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    y: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    z_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rotation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    props_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    style_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    bindings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

