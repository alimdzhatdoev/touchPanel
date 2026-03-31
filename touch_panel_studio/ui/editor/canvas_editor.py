from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from touch_panel_studio.db.models.component import Component
from touch_panel_studio.db.models.screen import Screen
from touch_panel_studio.db.repositories.component_repo import ComponentRepository
from touch_panel_studio.db.session import SessionFactory
from touch_panel_studio.domain.component_presets import (
    default_bindings,
    default_name_for_type,
    default_props_for_type,
    default_style_for_type,
)
from touch_panel_studio.ui.editor.canvas_view import CanvasView
from touch_panel_studio.ui.editor.grid_scene import GridScene
from touch_panel_studio.ui.editor.items.editor_component_item import EditorComponentItem


class CanvasEditorWidget(QWidget):
    def __init__(self, project_db: SessionFactory, assets_dir: Path | None = None) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._db = project_db
        self._repo = ComponentRepository()
        self._loaded: tuple[int, int, int] | None = None  # screen_id, screen_w, screen_h
        self._assets_dir = assets_dir.resolve() if assets_dir else None
        self.snap_to_grid = True
        # Буфер «Копировать» (Ctrl+C): вставка на текущий экран со смещением (Ctrl+V).
        self._clipboard: dict | None = None

        self.scene = GridScene()
        self.view = CanvasView()
        self.view.setScene(self.scene)

        row_shapes = QHBoxLayout()
        row_shapes.setSpacing(8)
        row_shapes.addWidget(QLabel("Фигуры:"))
        for label, handler in (
            ("Прямоугольник", lambda: self._add_component("shape.rectangle")),
            ("Эллипс", lambda: self._add_component("shape.ellipse")),
            ("Линия", lambda: self._add_component("shape.line")),
        ):
            b = QPushButton(label)
            b.setMinimumHeight(40)
            b.clicked.connect(handler)
            row_shapes.addWidget(b)

        row_content = QHBoxLayout()
        row_content.setSpacing(8)
        row_content.addWidget(QLabel("Контент:"))
        for label, handler in (
            ("Текст", lambda: self._add_component("text")),
            ("Кнопка", lambda: self._add_component("button")),
            ("Картинка", lambda: self._add_component("image")),
        ):
            b = QPushButton(label)
            b.setMinimumHeight(40)
            b.clicked.connect(handler)
            row_content.addWidget(b)

        hint = QLabel(
            "Подсказка: выберите элемент — справа свойства. Копирование: кнопки «Буфер» или Ctrl+C / "
            "вставка Ctrl+V / дублировать Ctrl+D."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 12px;")

        row_clip = QHBoxLayout()
        row_clip.setSpacing(8)
        self.btn_copy = QPushButton("Копировать")
        self.btn_paste = QPushButton("Вставить")
        self.btn_duplicate = QPushButton("Дублировать")
        self.btn_copy.setMinimumHeight(36)
        self.btn_paste.setMinimumHeight(36)
        self.btn_duplicate.setMinimumHeight(36)
        self.btn_copy.setToolTip("Копировать выделенный объект (Ctrl+C)")
        self.btn_paste.setToolTip("Вставить копию на экран (Ctrl+V)")
        self.btn_duplicate.setToolTip("Дублировать выделенный объект (Ctrl+D)")
        self.btn_copy.clicked.connect(self.copy_selected)
        self.btn_paste.clicked.connect(self.paste_clipboard)
        self.btn_duplicate.clicked.connect(self.duplicate_selected)
        row_clip.addWidget(QLabel("Буфер:"))
        row_clip.addWidget(self.btn_copy)
        row_clip.addWidget(self.btn_paste)
        row_clip.addWidget(self.btn_duplicate)
        row_clip.addStretch(1)

        top = QVBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        top.addLayout(row_shapes)
        top.addLayout(row_content)
        top.addLayout(row_clip)
        top.addWidget(hint)

        root = QVBoxLayout()
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addLayout(top)
        root.addWidget(self.view, 1)
        self.setLayout(root)

        for seq, fn in (
            (QKeySequence.StandardKey.Copy, self.copy_selected),
            (QKeySequence.StandardKey.Paste, self.paste_clipboard),
            (QKeySequence("Ctrl+D"), self.duplicate_selected),
        ):
            sc = QShortcut(seq, self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(1500)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._flush_geometry_updates)
        self._pending_geometry: dict[int, tuple[int, int, int, int]] = {}

        self.scene.selectionChanged.connect(self._on_selection_changed)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        QTimer.singleShot(0, self._refit_canvas)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refit_canvas()

    def _refit_canvas(self) -> None:
        if not self._loaded:
            return
        r = self.scene.sceneRect()
        if not r.isValid() or r.width() <= 0 or r.height() <= 0:
            return
        self.view.fitInView(r, Qt.AspectRatioMode.KeepAspectRatio)

    def set_assets_dir(self, assets_dir: Path | None) -> None:
        self._assets_dir = assets_dir.resolve() if assets_dir else None
        for it in self.scene.items():
            if isinstance(it, EditorComponentItem):
                it.set_assets_dir(assets_dir)

    def load_screen(self, screen_id: int) -> None:
        self.scene.clear()
        self._pending_geometry.clear()

        with self._db.session() as s:
            sc = s.get(Screen, screen_id)
            if sc is None:
                self._loaded = None
                return
            self._loaded = (int(sc.id), int(sc.width), int(sc.height))
            bg_type = str(sc.background_type or "color")
            bg_value = sc.background_value
            bg_fit = str(getattr(sc, "background_fit", None) or "contain")
            bg_scale = int(getattr(sc, "background_scale_percent", None) or 100)
            comps = self._repo.list_for_screen(s, screen_id=int(sc.id))
            self.scene.setSceneRect(0, 0, self._loaded[1], self._loaded[2])
            self.scene.set_screen_background(
                bg_type,
                bg_value,
                self._assets_dir,
                background_fit=bg_fit,
                background_scale_percent=bg_scale,
            )
            for c in comps:
                self._add_item_from_component(c)

        self.view.viewport().update()
        QTimer.singleShot(0, self._refit_canvas)

    def _apply_background(self) -> None:
        if not self._loaded:
            return
        with self._db.session() as s:
            sc = s.get(Screen, self._loaded[0])
            if sc is None:
                return
            bg_type = str(sc.background_type or "color")
            bg_value = sc.background_value
            bg_fit = str(getattr(sc, "background_fit", None) or "contain")
            bg_scale = int(getattr(sc, "background_scale_percent", None) or 100)
        self.scene.set_screen_background(
            bg_type,
            bg_value,
            self._assets_dir,
            background_fit=bg_fit,
            background_scale_percent=bg_scale,
        )
        self.view.viewport().update()

    def _add_item_from_component(self, c: Component) -> EditorComponentItem:
        it = EditorComponentItem.from_component(c, self._assets_dir)
        self.scene.addItem(it)
        return it

    def copy_selected(self) -> bool:
        """Сохраняет выделенный компонент в буфер для Вставить (Ctrl+V)."""
        it = self.selected_item()
        if it is None or self._loaded is None:
            return False
        cid = int(it.component_id)
        with self._db.session() as s:
            src = s.get(Component, cid)
            if src is None:
                return False
            x, y, w, h = it.geometry_int()
            self._clipboard = {
                "type": str(src.type),
                "name": src.name or "",
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "z_index": int(src.z_index),
                "rotation": int(src.rotation),
                "is_visible": bool(src.is_visible),
                "props_json": str(src.props_json),
                "style_json": str(src.style_json),
                "bindings_json": str(src.bindings_json),
            }
        return True

    def paste_clipboard(self) -> bool:
        """Создаёт копию из буфера на текущем экране (со смещением; повтор — лесенкой)."""
        if not self._clipboard or self._loaded is None:
            return False
        d = self._clipboard
        screen_id = self._loaded[0]
        x = int(d["x"]) + 20
        y = int(d["y"]) + 20
        base = (d["name"] or "").strip()
        name = (base + " (копия)") if base else "Копия"
        with self._db.session() as s:
            c = self._repo.create(
                s,
                screen_id=screen_id,
                type=str(d["type"]),
                name=name,
                x=x,
                y=y,
                width=int(d["width"]),
                height=int(d["height"]),
                z_index=int(d["z_index"]),
                rotation=int(d["rotation"]),
                is_visible=bool(d["is_visible"]),
                props_json=str(d["props_json"]),
                style_json=str(d["style_json"]),
                bindings_json=str(d["bindings_json"]),
            )
            s.commit()
            s.refresh(c)
            new_it = self._add_item_from_component(c)
        d["x"], d["y"] = x, y
        self.scene.clearSelection()
        new_it.setSelected(True)
        return True

    def _add_component(self, comp_type: str) -> None:
        if not self._loaded:
            return
        screen_id, _, _ = self._loaded
        props = default_props_for_type(comp_type)
        style = default_style_for_type(comp_type)
        bindings = default_bindings()
        name = default_name_for_type(comp_type)
        w, h = 180, 120
        if comp_type == "shape.line":
            w, h = 240, 12
        elif comp_type == "text":
            w, h = 280, 100
        elif comp_type == "button":
            w, h = 220, 56
        elif comp_type == "image":
            w, h = 240, 180
        elif comp_type == "shape.ellipse":
            w, h = 160, 160

        with self._db.session() as s:
            c = self._repo.create(
                s,
                screen_id=screen_id,
                type=comp_type,
                name=name,
                x=60,
                y=60,
                width=w,
                height=h,
                props_json=json.dumps(props, ensure_ascii=False),
                style_json=json.dumps(style, ensure_ascii=False),
                bindings_json=json.dumps(bindings, ensure_ascii=False),
            )
            s.commit()
            s.refresh(c)
            self._add_item_from_component(c)

    def _on_selection_changed(self) -> None:
        return

    def notify_item_geometry_changed(self, component_id: int, x: int, y: int, w: int, h: int) -> None:
        if self.snap_to_grid:
            gs = int(getattr(self.scene, "grid_size", 20) or 20)
            x = int(round(x / gs) * gs)
            y = int(round(y / gs) * gs)
            w = max(1, int(round(w / gs) * gs))
            h = max(1, int(round(h / gs) * gs))
            self._apply_geometry_to_item(component_id, x, y, w, h)
        self._pending_geometry[component_id] = (x, y, w, h)
        self._autosave_timer.start()

    def _apply_geometry_to_item(self, component_id: int, x: int, y: int, w: int, h: int) -> None:
        for it in self.scene.items():
            if isinstance(it, EditorComponentItem) and int(it.component_id) == int(component_id):
                from PySide6.QtCore import QRectF

                it.setPos(float(x), float(y))
                it.setRect(QRectF(0, 0, float(w), float(h)))
                break

    def selected_item(self) -> EditorComponentItem | None:
        for it in self.scene.selectedItems():
            if isinstance(it, EditorComponentItem):
                return it
        return None

    def refresh_component(self, component_id: int) -> None:
        with self._db.session() as s:
            c = s.get(Component, int(component_id))
            if c is None:
                return
            for it in self.scene.items():
                if isinstance(it, EditorComponentItem) and int(it.component_id) == int(component_id):
                    it.apply_component(c)
                    break

    def delete_selected(self) -> None:
        it = self.selected_item()
        if it is None:
            return
        cid = int(it.component_id)
        with self._db.session() as s:
            self._repo.delete(s, cid)
            s.commit()
        self.scene.removeItem(it)

    def duplicate_selected(self) -> None:
        """Один шаг: положить выделение в буфер и сразу вставить копию (как Ctrl+C, Ctrl+V)."""
        if not self.copy_selected():
            return
        self.paste_clipboard()

    def set_component_geometry(self, component_id: int, x: int, y: int, w: int, h: int) -> None:
        self._apply_geometry_to_item(component_id, x, y, w, h)
        self.notify_item_geometry_changed(component_id, x, y, w, h)

    def set_component_z(self, component_id: int, z_index: int) -> None:
        for it in self.scene.items():
            if isinstance(it, EditorComponentItem) and int(it.component_id) == int(component_id):
                it.setZValue(float(z_index))
                break
        with self._db.session() as s:
            self._repo.update_z(s, component_id=int(component_id), z_index=int(z_index))
            s.commit()

    def set_component_visible(self, component_id: int, visible: bool) -> None:
        for it in self.scene.items():
            if isinstance(it, EditorComponentItem) and int(it.component_id) == int(component_id):
                it.setVisible(bool(visible))
                break
        with self._db.session() as s:
            self._repo.update_visible(s, component_id=int(component_id), is_visible=bool(visible))
            s.commit()

    def update_component_payload(
        self,
        component_id: int,
        *,
        name: str,
        props: dict,
        style: dict,
        bindings: dict,
    ) -> None:
        with self._db.session() as s:
            self._repo.update_payload(
                s,
                int(component_id),
                name=name or None,
                props_json=json.dumps(props, ensure_ascii=False),
                style_json=json.dumps(style, ensure_ascii=False),
                bindings_json=json.dumps(bindings, ensure_ascii=False),
            )
            s.commit()
        self.refresh_component(component_id)

    def _flush_geometry_updates(self) -> None:
        if not self._pending_geometry:
            return
        pending = dict(self._pending_geometry)
        self._pending_geometry.clear()
        with self._db.session() as s:
            for cid, (x, y, w, h) in pending.items():
                self._repo.update_geometry(s, component_id=int(cid), x=int(x), y=int(y), width=int(w), height=int(h))
            s.commit()
