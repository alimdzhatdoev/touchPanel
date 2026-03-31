from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from touch_panel_studio.db.base import Base, TimestampMixin


class Screen(Base, TimestampMixin):
    __tablename__ = "screens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    screen_type: Mapped[str] = mapped_column(String(50), default="default", nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=1920, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_home: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    background_type: Mapped[str] = mapped_column(String(30), default="color", nullable=False)
    background_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Картинка: contain — вписать с полями; cover — заполнить с обрезкой; stretch — растянуть.
    background_fit: Mapped[str] = mapped_column(String(16), default="contain", nullable=False)
    background_scale_percent: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

