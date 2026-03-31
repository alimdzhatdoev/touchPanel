from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from touch_panel_studio.db.models.component import Component


@dataclass(frozen=True, slots=True)
class ComponentRepository:
    def list_for_screen(self, session: Session, screen_id: int) -> list[Component]:
        return list(session.scalars(select(Component).where(Component.screen_id == screen_id).order_by(Component.z_index.asc(), Component.id.asc())))

    def create(
        self,
        session: Session,
        screen_id: int,
        type: str,
        name: str | None,
        x: int,
        y: int,
        width: int,
        height: int,
        z_index: int = 0,
        rotation: int = 0,
        is_visible: bool = True,
        props_json: str = "{}",
        style_json: str = "{}",
        bindings_json: str = "{}",
    ) -> Component:
        c = Component(
            screen_id=screen_id,
            type=type,
            name=name,
            x=x,
            y=y,
            width=width,
            height=height,
            z_index=z_index,
            rotation=rotation,
            is_visible=is_visible,
            props_json=props_json,
            style_json=style_json,
            bindings_json=bindings_json,
        )
        session.add(c)
        session.flush()
        return c

    def delete(self, session: Session, component_id: int) -> None:
        session.execute(delete(Component).where(Component.id == component_id))

    def update_geometry(self, session: Session, component_id: int, x: int, y: int, width: int, height: int) -> None:
        session.execute(
            update(Component)
            .where(Component.id == component_id)
            .values(x=x, y=y, width=width, height=height)
        )

    def update_z(self, session: Session, component_id: int, z_index: int) -> None:
        session.execute(update(Component).where(Component.id == component_id).values(z_index=z_index))

    def update_visible(self, session: Session, component_id: int, is_visible: bool) -> None:
        session.execute(update(Component).where(Component.id == component_id).values(is_visible=is_visible))

    def update_payload(
        self,
        session: Session,
        component_id: int,
        *,
        name: str | None = None,
        props_json: str | None = None,
        style_json: str | None = None,
        bindings_json: str | None = None,
    ) -> None:
        vals: dict = {}
        if name is not None:
            vals["name"] = name
        if props_json is not None:
            vals["props_json"] = props_json
        if style_json is not None:
            vals["style_json"] = style_json
        if bindings_json is not None:
            vals["bindings_json"] = bindings_json
        if vals:
            session.execute(update(Component).where(Component.id == component_id).values(**vals))

