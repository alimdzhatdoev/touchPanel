from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from touch_panel_studio.db.models.screen import Screen


@dataclass(frozen=True, slots=True)
class ScreenRepository:
    def list_for_project(self, session: Session, project_id: int) -> list[Screen]:
        return list(
            session.scalars(
                select(Screen).where(Screen.project_id == project_id).order_by(Screen.sort_order.asc(), Screen.id.asc())
            )
        )

    def create(
        self,
        session: Session,
        project_id: int,
        name: str,
        slug: str,
        width: int = 1920,
        height: int = 1080,
    ) -> Screen:
        screen = Screen(
            project_id=project_id,
            name=name,
            slug=slug,
            width=width,
            height=height,
            sort_order=0,
            is_home=False,
            is_published=False,
        )
        session.add(screen)
        session.flush()
        return screen

    def delete(self, session: Session, screen_id: int) -> None:
        session.execute(delete(Screen).where(Screen.id == screen_id))

    def set_home(self, session: Session, project_id: int, screen_id: int) -> None:
        session.execute(update(Screen).where(Screen.project_id == project_id).values(is_home=False))
        session.execute(update(Screen).where(Screen.id == screen_id).values(is_home=True))

    def set_published(self, session: Session, screen_id: int, published: bool) -> None:
        session.execute(update(Screen).where(Screen.id == screen_id).values(is_published=published))

    def update_background(
        self,
        session: Session,
        screen_id: int,
        *,
        background_type: str,
        background_value: str | None,
    ) -> None:
        session.execute(
            update(Screen)
            .where(Screen.id == screen_id)
            .values(background_type=background_type, background_value=background_value)
        )

    def update_background_image_layout(
        self,
        session: Session,
        screen_id: int,
        *,
        background_fit: str,
        background_scale_percent: int,
    ) -> None:
        session.execute(
            update(Screen)
            .where(Screen.id == screen_id)
            .values(
                background_fit=str(background_fit),
                background_scale_percent=int(background_scale_percent),
            )
        )

    def update_dimensions(self, session: Session, screen_id: int, *, width: int, height: int) -> None:
        session.execute(
            update(Screen)
            .where(Screen.id == screen_id)
            .values(width=int(width), height=int(height))
        )

    def update_transition(self, session: Session, screen_id: int, *, transition_json: str) -> None:
        session.execute(
            update(Screen)
            .where(Screen.id == screen_id)
            .values(transition_json=str(transition_json))
        )

