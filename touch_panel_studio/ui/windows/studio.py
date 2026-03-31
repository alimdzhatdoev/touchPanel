from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sqlalchemy import select

from touch_panel_studio.app.context import AppContext
from touch_panel_studio.db.models.component import Component
from touch_panel_studio.db.models.project import Project
from touch_panel_studio.db.models.screen import Screen
from touch_panel_studio.db.repositories.screen_repo import ScreenRepository
from touch_panel_studio.infrastructure.storage.asset_import import import_file_into_assets
from touch_panel_studio.infrastructure.storage.editor_settings import EditorSettings, load_editor_settings, save_editor_settings
from touch_panel_studio.infrastructure.storage.project_storage import ProjectHandle
from touch_panel_studio.ui.widgets.color_line_edit import ColorLineEdit
from touch_panel_studio.ui.editor.canvas_editor import CanvasEditorWidget
from touch_panel_studio.ui.editor.property_inspector import InspectorFullState, PropertyInspectorWidget
from touch_panel_studio.ui.runtime.runtime_window import RuntimeWindow


def _aspect_lock_icon(locked: bool, size: int = 22) -> QIcon:
    """Плоская белая иконка замка (закрыт / открыт) для кнопки пропорций."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor("#ffffff"))
    pen.setWidthF(max(1.4, size / 14.0))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    s = float(size)
    m = s * 0.2
    body = QRectF(m, s * 0.46, s - 2.0 * m, s * 0.36)
    p.drawRoundedRect(body, 2.5, 2.5)
    if locked:
        sh = QRectF(s * 0.24, s * 0.12, s * 0.52, s * 0.4)
        p.drawArc(sh, 180 * 16, 180 * 16)
    else:
        sh = QRectF(s * 0.1, s * 0.12, s * 0.52, s * 0.4)
        p.drawArc(sh, 55 * 16, 255 * 16)
    p.end()
    return QIcon(pm)


@dataclass(frozen=True, slots=True)
class OpenProject:
    handle: ProjectHandle
    project_db_engine_title: str


class StudioWidget(QWidget):
    logout_requested = Signal()

    def __init__(self, ctx: AppContext, opened: OpenProject) -> None:
        super().__init__()
        self._ctx = ctx
        self._opened = opened
        self._repo = ScreenRepository()
        self._project_db = self._opened.handle.open_db()
        self._block_screen_bg = False
        self._block_screen_size = False
        self._aspect_ratio_wh = 1920.0 / 1080.0
        self._editor_settings = load_editor_settings(self._ctx.paths.config_dir)

        self.editor = CanvasEditorWidget(project_db=self._project_db, assets_dir=self._opened.handle.assets_dir)
        self.editor.scene.set_grid_opacity(self._editor_settings.grid_opacity)

        self.setObjectName("StudioWidget")

        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))

        self.btn_screen_new = QPushButton("Новый экран")
        self.btn_screen_delete = QPushButton("Удалить")
        self.btn_screen_home = QPushButton("Сделать домашним")
        self.btn_screen_publish = QPushButton("Опубликовать/Снять")
        for b in (self.btn_screen_new, self.btn_screen_delete, self.btn_screen_home, self.btn_screen_publish):
            b.setMinimumHeight(42)

        self.btn_screen_new.clicked.connect(self._on_new_screen)
        self.btn_screen_delete.clicked.connect(self._on_delete_screen)
        self.btn_screen_home.clicked.connect(self._on_set_home)
        self.btn_screen_publish.clicked.connect(self._on_toggle_publish)

        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        left_layout.addWidget(QLabel("Экраны"))
        self.screens = QListWidget()
        self.screens.setStyleSheet("font-size: 16px;")
        self.screens.currentItemChanged.connect(self._on_selected_changed)
        left_layout.addWidget(self.screens, 1)

        self.screen_size_group = QGroupBox("Размер экрана (px)")
        self.screen_width = QSpinBox()
        self.screen_width.setRange(320, 8192)
        self.screen_width.setSingleStep(8)
        self.screen_height = QSpinBox()
        self.screen_height.setRange(240, 8192)
        self.screen_height.setSingleStep(8)
        self.screen_aspect_lock = QToolButton()
        self.screen_aspect_lock.setCheckable(True)
        self.screen_aspect_lock.setToolTip(
            "Связать ширину и высоту по пропорции. При включении пропорция берётся из текущих чисел."
        )
        self.screen_aspect_lock.setAccessibleName("Связать пропорции ширины и высоты")
        self.screen_aspect_lock.blockSignals(True)
        self.screen_aspect_lock.setChecked(True)
        self.screen_aspect_lock.blockSignals(False)
        self.screen_aspect_lock.setIconSize(QSize(20, 20))
        self.screen_aspect_lock.setStyleSheet(
            "QToolButton { background: transparent; border: none; padding: 2px; min-width: 24px; min-height: 24px; }"
            "QToolButton:hover { background: rgba(255, 255, 255, 0.08); border-radius: 4px; }"
        )
        self.screen_aspect_lock.toggled.connect(self._on_screen_aspect_lock_toggled)
        self._apply_screen_aspect_lock_icon()
        size_row = QWidget()
        srl = QHBoxLayout(size_row)
        srl.setContentsMargins(0, 0, 0, 0)
        srl.setSpacing(8)
        srl.addWidget(self.screen_width)
        srl.addWidget(QLabel("×"))
        srl.addWidget(self.screen_height)
        srl.addWidget(self.screen_aspect_lock)
        sz_form = QFormLayout()
        sz_form.setSpacing(8)
        sz_form.addRow("Ширина × высота", size_row)
        self.screen_size_group.setLayout(sz_form)
        self.screen_width.valueChanged.connect(self._on_screen_size_changed)
        self.screen_height.valueChanged.connect(self._on_screen_size_changed)

        self.screen_bg_group = QGroupBox("Фон экрана")
        self.screen_bg_type = QComboBox()
        self.screen_bg_type.addItem("Цвет", "color")
        self.screen_bg_type.addItem("Картинка", "image")
        self.screen_bg_color = ColorLineEdit()
        self.screen_bg_color.setPlaceholderText("#ffffff")
        self.screen_bg_image = QLineEdit()
        self.screen_bg_image.setPlaceholderText("или «Загрузить…» — файл скопируется в assets")
        self.screen_bg_import = QPushButton("Загрузить…")
        self.screen_bg_import.setMinimumWidth(100)
        screen_bg_img_row = QWidget()
        sbr = QHBoxLayout(screen_bg_img_row)
        sbr.setContentsMargins(0, 0, 0, 0)
        sbr.addWidget(self.screen_bg_image, 1)
        sbr.addWidget(self.screen_bg_import)
        bg_form = QFormLayout()
        bg_form.setSpacing(8)
        bg_form.addRow("Тип", self.screen_bg_type)
        bg_form.addRow("Цвет", self.screen_bg_color)
        bg_form.addRow("Картинка", screen_bg_img_row)
        self.screen_bg_fit = QComboBox()
        self.screen_bg_fit.addItem("Вписать (пропорции)", "contain")
        self.screen_bg_fit.addItem("Заполнить (обрезка)", "cover")
        self.screen_bg_fit.addItem("Растянуть", "stretch")
        self.screen_bg_scale = QSpinBox()
        self.screen_bg_scale.setRange(50, 300)
        self.screen_bg_scale.setSingleStep(5)
        self.screen_bg_scale.setSuffix(" %")
        self.screen_bg_scale.setValue(100)
        self.screen_bg_scale.setToolTip("Масштаб относительно режима «вписать» / «заполнить» (100% = по умолчанию)")
        bg_form.addRow("Режим картинки", self.screen_bg_fit)
        bg_form.addRow("Масштаб картинки", self.screen_bg_scale)
        self.screen_bg_group.setLayout(bg_form)
        self.screen_bg_type.currentIndexChanged.connect(self._on_screen_bg_kind_changed)
        self.screen_bg_color.editingFinished.connect(self._save_screen_background)
        self.screen_bg_image.editingFinished.connect(self._save_screen_background)
        self.screen_bg_import.clicked.connect(self._import_screen_background_image)
        self.screen_bg_fit.currentIndexChanged.connect(self._save_screen_bg_layout)
        self.screen_bg_scale.valueChanged.connect(self._save_screen_bg_layout)

        self.editor_grid_group = QGroupBox("Сетка канваса")
        grid_form = QFormLayout()
        grid_form.setSpacing(8)
        self.grid_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.grid_opacity_slider.setRange(0, 100)
        self.grid_opacity_slider.setValue(int(self._editor_settings.grid_opacity * 100))
        self.grid_opacity_slider.setToolTip("0 — сетка скрыта")
        grid_form.addRow("Прозрачность сетки", self.grid_opacity_slider)
        self.editor_grid_group.setLayout(grid_form)
        self.grid_opacity_slider.valueChanged.connect(self._on_grid_opacity_changed)

        left_layout.addWidget(self.screen_size_group)
        left_layout.addWidget(self.screen_bg_group)
        left_layout.addWidget(self.editor_grid_group)
        left_layout.addWidget(self.btn_screen_new)
        left_layout.addWidget(self.btn_screen_home)
        left_layout.addWidget(self.btn_screen_publish)
        left_layout.addWidget(self.btn_screen_delete)
        left.setLayout(left_layout)

        self.canvas = QFrame()
        self.canvas.setFrameShape(QFrame.StyledPanel)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        canvas_layout = QVBoxLayout()
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        canvas_layout.addWidget(self.editor, 1)
        self.canvas.setLayout(canvas_layout)

        self.inspector = QFrame()
        self.inspector.setFrameShape(QFrame.StyledPanel)
        insp_layout = QVBoxLayout()
        insp_layout.setContentsMargins(0, 0, 0, 0)
        insp_layout.setSpacing(0)
        self.props = PropertyInspectorWidget()
        self.props.set_assets_dir(self._opened.handle.assets_dir)
        self.props.geometry_changed.connect(self._on_inspector_geometry)
        self.props.z_changed.connect(self._on_inspector_z)
        self.props.visible_changed.connect(self._on_inspector_visible)
        self.props.data_changed.connect(self._on_inspector_data)
        insp_layout.addWidget(self.props, 1)
        self.inspector.setLayout(insp_layout)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.inspector)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setCollapsible(2, False)
        splitter.setSizes([300, 720, 420])

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._make_topbar())
        root.addWidget(splitter, 1)
        self.setLayout(root)

        self.editor.scene.selectionChanged.connect(self._sync_inspector_from_selection)
        self.reload_screens()
        self._refresh_action_targets()
        if self.screens.count() > 0:
            self.screens.setCurrentRow(0)

    def _make_topbar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        title = QLabel(f"Studio — {self._opened.handle.meta.name} ({self._opened.handle.meta.code})")
        title.setStyleSheet("font-size: 18px; font-weight: 650;")
        layout.addWidget(title)
        layout.addStretch(1)
        self.btn_runtime = QPushButton("▶ Runtime")
        self.btn_runtime.setMinimumHeight(40)
        self.btn_runtime.clicked.connect(self._on_runtime)
        layout.addWidget(self.btn_runtime)
        self.btn_back = QPushButton("← Проекты")
        self.btn_back.setMinimumHeight(40)
        # сигнал подключим в контроллере через публичный callback
        layout.addWidget(self.btn_back)
        self.btn_logout = QPushButton("Выход")
        self.btn_logout.setMinimumHeight(40)
        self.btn_logout.clicked.connect(self.logout_requested.emit)
        layout.addWidget(self.btn_logout)
        bar.setLayout(layout)
        return bar

    def reload_screens(self) -> None:
        self.screens.clear()
        sf = self._opened.handle.open_db()
        with sf.session() as s:
            project_id = s.scalar(select(Project.id).limit(1))
            if project_id is None:
                project_id = 1
            items = self._repo.list_for_project(s, int(project_id))

        for sc in items:
            label = f"{'Домой • ' if sc.is_home else ''}{sc.name}  [{sc.slug}]"
            if sc.is_published:
                label += "  • опубликован"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, int(sc.id))
            self.screens.addItem(item)
        self._refresh_action_targets()

    def _selected_screen_id(self) -> int | None:
        it = self.screens.currentItem()
        if not it:
            return None
        v = it.data(Qt.UserRole)
        return int(v) if v is not None else None

    def _on_new_screen(self) -> None:
        # MVP: авто-генерация имени/slug. Следующий этап: диалог параметров.
        sf = self._opened.handle.open_db()
        with sf.session() as s:
            # Single-project DB assumption: project id = first row id.
            pid = s.scalar(select(Project.id).limit(1)) or 1
            existing = self._repo.list_for_project(s, int(pid))
            n = len(existing) + 1
            self._repo.create(s, project_id=int(pid), name=f"Экран {n}", slug=f"screen-{n}")
            s.commit()
        self.reload_screens()

    def _on_delete_screen(self) -> None:
        sid = self._selected_screen_id()
        if not sid:
            return
        sf = self._opened.handle.open_db()
        with sf.session() as s:
            self._repo.delete(s, sid)
            s.commit()
        self.reload_screens()

    def _on_set_home(self) -> None:
        sid = self._selected_screen_id()
        if not sid:
            return
        sf = self._opened.handle.open_db()
        with sf.session() as s:
            pid = s.scalar(select(Project.id).limit(1)) or 1
            self._repo.set_home(s, project_id=int(pid), screen_id=sid)
            s.commit()
        self.reload_screens()

    def _on_toggle_publish(self) -> None:
        sid = self._selected_screen_id()
        if not sid:
            return
        sf = self._opened.handle.open_db()
        with sf.session() as s:
            sc = s.get(Screen, sid)
            if sc is None:
                return
            self._repo.set_published(s, sid, not bool(sc.is_published))
            s.commit()
        self.reload_screens()

    def _on_selected_changed(self, current: QListWidgetItem | None, prev: QListWidgetItem | None) -> None:
        _ = prev
        if not current:
            self.props.set_state(None)
            return
        sid = current.data(Qt.UserRole)
        if sid is None:
            self.props.set_state(None)
            return
        self.editor.load_screen(int(sid))
        self._load_screen_panel()
        self._sync_inspector_from_selection()

    def _on_screen_bg_kind_changed(self) -> None:
        self._sync_screen_bg_fields_visibility()
        self._save_screen_background()

    def _sync_screen_bg_fields_visibility(self) -> None:
        t = self.screen_bg_type.currentData()
        self.screen_bg_color.setVisible(t == "color")
        self.screen_bg_image.setVisible(t == "image")
        self.screen_bg_fit.setVisible(t == "image")
        self.screen_bg_scale.setVisible(t == "image")

    def _load_screen_panel(self) -> None:
        sid = self._selected_screen_id()
        if not sid:
            self.screen_size_group.setEnabled(False)
            self.screen_bg_group.setEnabled(False)
            return
        self.screen_size_group.setEnabled(True)
        self.screen_bg_group.setEnabled(True)
        with self._project_db.session() as s:
            sc = s.get(Screen, sid)
            if sc is None:
                return
            self._block_screen_size = True
            self._block_screen_bg = True
            try:
                self.screen_width.setValue(int(sc.width))
                self.screen_height.setValue(int(sc.height))

                bt = (sc.background_type or "color").lower()
                self.screen_bg_type.setCurrentIndex(0 if bt == "color" else 1)
                if bt == "color":
                    self.screen_bg_color.setText(sc.background_value or "#ffffff")
                else:
                    self.screen_bg_image.setText(sc.background_value or "")
                fit = str(getattr(sc, "background_fit", None) or "contain")
                self.screen_bg_fit.setCurrentIndex({"contain": 0, "cover": 1, "stretch": 2}.get(fit.lower(), 0))
                self.screen_bg_scale.setValue(int(getattr(sc, "background_scale_percent", None) or 100))
            finally:
                self._block_screen_size = False
                self._block_screen_bg = False
        self._sync_aspect_ratio_from_spinboxes()
        self._sync_screen_bg_fields_visibility()

    def _sync_aspect_ratio_from_spinboxes(self) -> None:
        w = max(1, int(self.screen_width.value()))
        h = max(1, int(self.screen_height.value()))
        self._aspect_ratio_wh = w / float(h)

    def _apply_screen_aspect_lock_icon(self) -> None:
        self.screen_aspect_lock.setIcon(_aspect_lock_icon(self.screen_aspect_lock.isChecked()))
        self.screen_aspect_lock.setText("")

    def _on_screen_aspect_lock_toggled(self, checked: bool) -> None:
        self._apply_screen_aspect_lock_icon()
        if checked:
            self._sync_aspect_ratio_from_spinboxes()

    def _on_screen_size_changed(self) -> None:
        if self._block_screen_size:
            return
        sid = self._selected_screen_id()
        if not sid:
            return
        if self.screen_aspect_lock.isChecked():
            sender = self.sender()
            self._block_screen_size = True
            try:
                if sender is self.screen_width:
                    w = int(self.screen_width.value())
                    h = int(round(w / self._aspect_ratio_wh))
                    h = max(240, min(8192, h))
                    self.screen_height.blockSignals(True)
                    self.screen_height.setValue(h)
                    self.screen_height.blockSignals(False)
                elif sender is self.screen_height:
                    h = int(self.screen_height.value())
                    w = int(round(h * self._aspect_ratio_wh))
                    w = max(320, min(8192, w))
                    self.screen_width.blockSignals(True)
                    self.screen_width.setValue(w)
                    self.screen_width.blockSignals(False)
            finally:
                self._block_screen_size = False
        w = int(self.screen_width.value())
        h = int(self.screen_height.value())
        if w < 1 or h < 1:
            return
        with self._project_db.session() as s:
            self._repo.update_dimensions(s, sid, width=w, height=h)
            s.commit()
        self.editor.load_screen(sid)
        self._sync_inspector_from_selection()

    def _save_screen_background(self) -> None:
        if self._block_screen_bg:
            return
        sid = self._selected_screen_id()
        if not sid:
            return
        t = self.screen_bg_type.currentData()
        if t == "color":
            val = self.screen_bg_color.text().strip() or "#ffffff"
        else:
            val = self.screen_bg_image.text().strip()
        with self._project_db.session() as s:
            self._repo.update_background(s, sid, background_type=str(t), background_value=val or None)
            s.commit()
        self.editor.load_screen(sid)
        self._sync_inspector_from_selection()

    def _on_grid_opacity_changed(self, v: int) -> None:
        a = max(0.0, min(1.0, v / 100.0))
        self._editor_settings = EditorSettings(grid_opacity=a)
        save_editor_settings(self._ctx.paths.config_dir, self._editor_settings)
        self.editor.scene.set_grid_opacity(a)

    def _save_screen_bg_layout(self) -> None:
        if self._block_screen_bg:
            return
        sid = self._selected_screen_id()
        if not sid:
            return
        fit = str(self.screen_bg_fit.currentData())
        scale = int(self.screen_bg_scale.value())
        with self._project_db.session() as s:
            self._repo.update_background_image_layout(s, sid, background_fit=fit, background_scale_percent=scale)
            s.commit()
        self.editor.load_screen(sid)
        self._sync_inspector_from_selection()

    def _import_screen_background_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Фон экрана — выберите изображение",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg);;Все файлы (*.*)",
        )
        if not path:
            return
        try:
            rel = import_file_into_assets(self._opened.handle.assets_dir, Path(path))
        except Exception as e:
            QMessageBox.critical(self, "Не удалось сохранить файл", str(e))
            return
        self._block_screen_bg = True
        try:
            self.screen_bg_type.setCurrentIndex(1)
            self.screen_bg_image.setText(rel)
        finally:
            self._block_screen_bg = False
        self._sync_screen_bg_fields_visibility()
        self._save_screen_background()

    def _refresh_action_targets(self) -> None:
        sf = self._opened.handle.open_db()
        with sf.session() as s:
            pid = s.scalar(select(Project.id).limit(1)) or 1
            screens = self._repo.list_for_project(s, int(pid))
        self.props.set_action_screens([(int(sc.id), f"{sc.name} ({sc.slug})") for sc in screens])

    def _sync_inspector_from_selection(self) -> None:
        it = self.editor.selected_item()
        if it is None:
            self.props.set_state(None)
            return
        cid = int(it.component_id)
        x, y, w, h = it.geometry_int()
        with self._project_db.session() as s:
            c = s.get(Component, cid)
            if c is None:
                self.props.set_state(None)
                return
            props = json.loads(c.props_json or "{}")
            style = json.loads(c.style_json or "{}")
            bindings = json.loads(c.bindings_json or "{}")
            comp_type = str(c.type)
            name = c.name or ""
        self.props.set_state(
            InspectorFullState(
                component_id=cid,
                comp_type=comp_type,
                name=name,
                x=x,
                y=y,
                width=w,
                height=h,
                z_index=int(it.zValue()),
                visible=bool(it.isVisible()),
                props=props,
                style=style,
                bindings=bindings,
            )
        )

    def _on_inspector_geometry(self, component_id: int, x: int, y: int, w: int, h: int) -> None:
        self.editor.set_component_geometry(component_id, x, y, w, h)

    def _on_inspector_z(self, component_id: int, z: int) -> None:
        self.editor.set_component_z(component_id, z)
        self._sync_inspector_from_selection()

    def _on_inspector_visible(self, component_id: int, v: bool) -> None:
        self.editor.set_component_visible(component_id, v)
        self._sync_inspector_from_selection()

    def _on_inspector_data(self, component_id: int, name: str, props: dict, style: dict, bindings: dict) -> None:
        self.editor.update_component_payload(component_id, name=name, props=props, style=style, bindings=bindings)
        self._sync_inspector_from_selection()

    def _on_runtime(self) -> None:
        w = RuntimeWindow(project_db=self._project_db, home_timeout_sec=60, assets_dir=self._opened.handle.assets_dir)
        w.showFullScreen()

