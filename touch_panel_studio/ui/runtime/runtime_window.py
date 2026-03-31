from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget, QWidget

from sqlalchemy import select

from touch_panel_studio.db.models.component import Component
from touch_panel_studio.db.models.screen import Screen
from touch_panel_studio.db.models.screen_action import ScreenAction
from touch_panel_studio.core.branding import app_logo_path
from touch_panel_studio.db.session import SessionFactory
from touch_panel_studio.ui.runtime.runtime_renderer import RuntimeRenderer


@dataclass(slots=True)
class NavState:
    history: list[int]
    current_screen_id: int | None = None
    home_screen_id: int | None = None


def _safe_json(s: str) -> dict:
    try:
        v = json.loads(s or "{}")
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


class _ActivityFilter(QObject):
    def __init__(self, on_activity) -> None:
        super().__init__()
        self._on_activity = on_activity

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if event.type() in (
            QEvent.MouseMove,
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
            QEvent.TouchBegin,
            QEvent.TouchUpdate,
            QEvent.TouchEnd,
            QEvent.KeyPress,
        ):
            self._on_activity()
        return False


class RuntimeWindow(QMainWindow):
    def __init__(self, project_db: SessionFactory, home_timeout_sec: int = 60, assets_dir: Path | None = None) -> None:
        super().__init__()
        self._db = project_db
        self._assets_dir = assets_dir
        self._renderer = RuntimeRenderer()
        self._nav = NavState(history=[])

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._widgets_by_screen: dict[int, QWidget] = {}
        self._home_timeout_sec = int(home_timeout_sec)
        self._home_timer = QTimer(self)
        self._home_timer.setSingleShot(True)
        self._home_timer.timeout.connect(self.go_home)

        self._activity_filter = _ActivityFilter(self._reset_home_timer)
        self.installEventFilter(self._activity_filter)

        self.setWindowTitle("Runtime Player")
        lp = app_logo_path()
        if lp is not None:
            self.setWindowIcon(QIcon(str(lp)))
        self.setWindowFlag(Qt.FramelessWindowHint, True)

        self._load_and_start()

    def _load_and_start(self) -> None:
        with self._db.session() as s:
            published = list(
                s.scalars(
                    select(Screen).where(Screen.is_published == True).order_by(Screen.sort_order.asc(), Screen.id.asc())  # noqa: E712
                )
            )
            if not published:
                QMessageBox.information(self, "Runtime", "Нет опубликованных экранов.")
                return

            home = next((sc for sc in published if sc.is_home), None) or published[0]
            self._nav.home_screen_id = int(home.id)

        self.open_screen(int(home.id), push_history=False)
        self._reset_home_timer()

    def _reset_home_timer(self) -> None:
        if self._home_timeout_sec <= 0:
            return
        self._home_timer.start(self._home_timeout_sec * 1000)

    def open_screen(self, screen_id: int, push_history: bool = True) -> None:
        if push_history and self._nav.current_screen_id is not None:
            self._nav.history.append(int(self._nav.current_screen_id))

        self._nav.current_screen_id = int(screen_id)
        w = self._widgets_by_screen.get(int(screen_id))
        if w is None:
            w = self._build_screen_widget(int(screen_id))
            if w is None:
                return
            self._widgets_by_screen[int(screen_id)] = w
            self._stack.addWidget(w)

        self._stack.setCurrentWidget(w)
        self._reset_home_timer()

    def go_back(self) -> None:
        if not self._nav.history:
            self.go_home()
            return
        prev = self._nav.history.pop()
        self.open_screen(int(prev), push_history=False)

    def go_home(self) -> None:
        if self._nav.home_screen_id is None:
            return
        self._nav.history.clear()
        self.open_screen(int(self._nav.home_screen_id), push_history=False)

    def _build_screen_widget(self, screen_id: int) -> QWidget | None:
        with self._db.session() as s:
            screen = s.get(Screen, screen_id)
            if screen is None:
                return None
            comps = list(s.scalars(select(Component).where(Component.screen_id == int(screen.id))))
            actions = list(s.scalars(select(ScreenAction).where(ScreenAction.source_screen_id == int(screen.id))))

        actions_by_component: dict[int, list[ScreenAction]] = {}
        for a in actions:
            if a.source_component_id is None:
                continue
            actions_by_component.setdefault(int(a.source_component_id), []).append(a)

        def on_component_clicked(component_id: int) -> None:
            # 1) screen_actions table
            for a in actions_by_component.get(int(component_id), []):
                if (a.action_type or "").lower() == "open_screen" and a.target_screen_id:
                    self.open_screen(int(a.target_screen_id))
                    return
                if (a.action_type or "").lower() == "back":
                    self.go_back()
                    return
                if (a.action_type or "").lower() == "home":
                    self.go_home()
                    return

            # 2) fallback: bindings_json from component
            c = next((x for x in comps if int(x.id) == int(component_id)), None)
            if c is None:
                return
            bindings = _safe_json(c.bindings_json)
            action = bindings.get("on_click") if isinstance(bindings, dict) else None
            if isinstance(action, dict):
                t = str(action.get("type", "")).lower()
                if t in ("none", ""):
                    return
                if t == "open_screen" and action.get("target_screen_id"):
                    self.open_screen(int(action["target_screen_id"]))
                elif t == "back":
                    self.go_back()
                elif t == "home":
                    self.go_home()
                elif t == "open_url":
                    url = str(action.get("url", "")).strip()
                    if url:
                        QDesktopServices.openUrl(QUrl(url))

        return self._renderer.build_screen_widget(
            screen=screen,
            components=comps,
            on_component_clicked=on_component_clicked,
            assets_dir=self._assets_dir,
        )

