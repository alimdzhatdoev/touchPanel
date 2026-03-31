from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from touch_panel_studio.ui.widgets.color_line_edit import ColorLineEdit


@dataclass(frozen=True, slots=True)
class InspectorFullState:
    component_id: int
    comp_type: str
    name: str
    x: int
    y: int
    width: int
    height: int
    z_index: int
    visible: bool
    props: dict[str, Any]
    style: dict[str, Any]
    bindings: dict[str, Any]


class PropertyInspectorWidget(QWidget):
    geometry_changed = Signal(int, int, int, int, int)
    z_changed = Signal(int, int)
    visible_changed = Signal(int, bool)
    """Имя и JSON-поля компонента (полные словари)."""
    data_changed = Signal(int, str, dict, dict, dict)

    def __init__(self) -> None:
        super().__init__()
        self._state: InspectorFullState | None = None
        self._block = False
        self._inspector_text_component_id: int | None = None
        self._action_screens: list[tuple[int, str]] = []
        self._assets_dir: Path | None = None

        title = QLabel("Свойства")
        title.setStyleSheet("font-size: 18px; font-weight: 650;")

        self.comp_type_label = QLabel("—")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Имя в дереве / подсказка")

        self.x = QSpinBox()
        self.y = QSpinBox()
        self.w = QSpinBox()
        self.h = QSpinBox()
        self.z = QSpinBox()
        for s in (self.x, self.y, self.w, self.h, self.z):
            s.setRange(-10_000, 10_000)
            s.setSingleStep(1)
            s.setMinimumHeight(32)
        self.w.setRange(1, 10_000)
        self.h.setRange(1, 10_000)

        self.visible = QCheckBox("Виден")
        self.visible.setChecked(True)

        geo = QGroupBox("Геометрия")
        gf = QFormLayout()
        gf.setSpacing(8)
        gf.addRow("X", self.x)
        gf.addRow("Y", self.y)
        gf.addRow("Ширина", self.w)
        gf.addRow("Высота", self.h)
        gf.addRow("Z", self.z)
        gf.addRow("", self.visible)
        geo.setLayout(gf)

        self.fill_edit = ColorLineEdit()
        self.stroke_edit = ColorLineEdit()
        self.stroke_w = QSpinBox()
        self.stroke_w.setRange(0, 64)
        self.radius = QSpinBox()
        self.radius.setRange(0, 500)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.0, 1.0)
        self.opacity.setSingleStep(0.05)

        self.look_group = QGroupBox("Внешний вид")
        lf = QFormLayout()
        lf.setSpacing(8)
        lf.addRow("Заливка", self.fill_edit)
        lf.addRow("Обводка", self.stroke_edit)
        lf.addRow("Толщина обводки", self.stroke_w)
        lf.addRow("Скругление (px)", self.radius)
        lf.addRow("Прозрачность", self.opacity)
        self.look_group.setLayout(lf)

        self.content_text = QLineEdit()
        self.content_text.setPlaceholderText("Подпись кнопки")
        self.text_multiline = QPlainTextEdit()
        self.text_multiline.setPlaceholderText("Текст; Enter — новая строка")
        self.text_multiline.setMinimumHeight(100)
        self.text_stack = QStackedWidget()
        self.text_stack.addWidget(self.content_text)
        self.text_stack.addWidget(self.text_multiline)

        self.font_size = QSpinBox()
        self.font_size.setRange(6, 400)
        self.font_family = QComboBox()
        self.font_family.setEditable(True)
        self.font_family.setMinimumHeight(32)
        self.font_family.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.font_family.addItems(sorted(QFontDatabase.families()))
        self.text_color = ColorLineEdit()
        self.align = QComboBox()
        self.align.addItems(["left", "center", "right"])
        self.valign = QComboBox()
        self.valign.addItem("Сверху", "top")
        self.valign.addItem("По центру", "center")
        self.valign.addItem("Снизу", "bottom")
        self.text_case = QComboBox()
        self.text_case.addItem("Как в тексте", "none")
        self.text_case.addItem("ВСЕ ПРОПИСНЫЕ", "upper")
        self.text_case.addItem("все строчные", "lower")
        self.text_case.addItem("Первая буква (весь текст)", "first")
        self.text_case.addItem("Предложение (каждая строка)", "capitalize")
        self.text_case.addItem("Каждое слово", "title")
        self.text_case.setToolTip(
            "Регистр только на экране и при запуске; в поле «Текст» хранится то, что вы ввели."
        )
        self.image_src = QLineEdit()
        self.icon_src = QLineEdit()
        self.icon_src.setPlaceholderText("или нажмите «Загрузить…»")
        self.icon_src.setToolTip(
            "Только у типа «Кнопка»: маленькая картинка слева от подписи на кнопке (путь в assets)."
        )
        self.image_src.setToolTip(
            "Только у типа «Изображение»: файл на весь прямоугольник компонента (отдельный блок на экране)."
        )

        self.button_bg_src = QLineEdit()
        self.button_bg_src.setPlaceholderText("фон на всю область кнопки")
        self.button_bg_src.setToolTip("Картинка фона кнопки (на весь прямоугольник); путь в assets или «Загрузить…».")

        self.btn_import_icon = QPushButton("Загрузить…")
        self.btn_import_icon.setMinimumWidth(100)
        self.btn_import_icon.setToolTip("Скопировать файл в папку assets проекта")

        self.btn_import_image = QPushButton("Загрузить…")
        self.btn_import_image.setMinimumWidth(100)
        self.btn_import_image.setToolTip("Скопировать файл в папку assets проекта")

        self.btn_import_button_bg = QPushButton("Загрузить…")
        self.btn_import_button_bg.setMinimumWidth(100)
        self.btn_import_button_bg.setToolTip("Скопировать файл в папку assets проекта")

        self.icon_block = QWidget()
        ib = QVBoxLayout(self.icon_block)
        ib.setContentsMargins(0, 0, 0, 0)
        ib.setSpacing(6)
        ib.addWidget(self.icon_src)
        ib.addWidget(self.btn_import_icon)

        self.button_bg_block = QWidget()
        bb = QVBoxLayout(self.button_bg_block)
        bb.setContentsMargins(0, 0, 0, 0)
        bb.setSpacing(6)
        bb.addWidget(self.button_bg_src)
        bb.addWidget(self.btn_import_button_bg)

        self.image_block = QWidget()
        img_l = QVBoxLayout(self.image_block)
        img_l.setContentsMargins(0, 0, 0, 0)
        img_l.setSpacing(6)
        img_l.addWidget(self.image_src)
        img_l.addWidget(self.btn_import_image)

        self.letter_spacing = QSpinBox()
        self.letter_spacing.setRange(50, 300)
        self.letter_spacing.setValue(100)
        self.letter_spacing.setSuffix(" %")
        self.letter_spacing.setToolTip("100% — как в шрифте; больше — шире буквы")
        self.line_height_pct = QSpinBox()
        self.line_height_pct.setRange(80, 250)
        self.line_height_pct.setValue(120)
        self.line_height_pct.setSuffix(" %")
        self.line_height_pct.setToolTip("Межстрочный интервал (для нескольких строк)")
        self.font_weight = QComboBox()
        for label, w in (
            ("Обычный", 400),
            ("Средний", 500),
            ("Полужирный", 600),
            ("Жирный", 700),
            ("Чёрный", 900),
        ):
            self.font_weight.addItem(label, int(w))
        self.text_italic = QCheckBox("Курсив")
        self.text_underline = QCheckBox("Подчёркнутый")

        self.typo_group = QGroupBox("Типографика")
        tf = QFormLayout()
        tf.setSpacing(8)
        tf.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        tf.addRow("Размер шрифта", self.font_size)
        tf.addRow("Шрифт", self.font_family)
        tf.addRow("Цвет текста", self.text_color)
        tf.addRow("По горизонтали", self.align)
        tf.addRow("По вертикали", self.valign)
        tf.addRow("Регистр букв", self.text_case)
        tf.addRow("Интервал букв", self.letter_spacing)
        tf.addRow("Высота строки", self.line_height_pct)
        tf.addRow("Начертание", self.font_weight)
        tf.addRow("", self.text_italic)
        tf.addRow("", self.text_underline)
        self.typo_group.setLayout(tf)

        self.content_group = QGroupBox("Контент")
        cf = QFormLayout()
        cf.setSpacing(8)
        cf.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        cf.addRow("Текст", self.text_stack)
        cf.addRow("Иконка кнопки", self.icon_block)
        cf.addRow("Фон кнопки", self.button_bg_block)
        cf.addRow("Файл изображения", self.image_block)
        self.content_group.setLayout(cf)

        self.action_kind = QComboBox()
        self.action_kind.addItems(["none", "open_screen", "open_url", "back", "home"])
        self.action_screen = QComboBox()
        self.action_url = QLineEdit()
        self.action_url.setPlaceholderText("https://…")

        act = QGroupBox("Действие по нажатию")
        af = QFormLayout()
        af.setSpacing(8)
        af.addRow("Тип", self.action_kind)
        af.addRow("Экран", self.action_screen)
        af.addRow("URL", self.action_url)
        act.setLayout(af)

        inner = QWidget()
        il = QVBoxLayout()
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(10)
        il.addWidget(QLabel("Тип"))
        il.addWidget(self.comp_type_label)
        il.addWidget(QLabel("Имя"))
        il.addWidget(self.name_edit)
        il.addWidget(geo)
        il.addWidget(self.look_group)
        il.addWidget(self.content_group)
        il.addWidget(self.typo_group)
        il.addWidget(act)
        il.addStretch(1)
        inner.setLayout(il)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(scroll, 1)
        self.setLayout(layout)
        self.setMinimumWidth(400)
        inner.setMinimumWidth(360)

        self.x.valueChanged.connect(self._emit_geometry)
        self.y.valueChanged.connect(self._emit_geometry)
        self.w.valueChanged.connect(self._emit_geometry)
        self.h.valueChanged.connect(self._emit_geometry)
        self.z.valueChanged.connect(self._emit_z)
        self.visible.toggled.connect(self._emit_visible)

        self.name_edit.editingFinished.connect(self._emit_data)
        for w in (
            self.fill_edit,
            self.stroke_edit,
            self.stroke_w,
            self.radius,
            self.opacity,
            self.content_text,
            self.font_size,
            self.text_color,
            self.action_url,
        ):
            if isinstance(w, QSpinBox):
                w.valueChanged.connect(self._emit_data)
            elif isinstance(w, QDoubleSpinBox):
                w.valueChanged.connect(self._emit_data)
            else:
                w.editingFinished.connect(self._emit_data)
        self.font_family.currentTextChanged.connect(self._emit_data)
        self.image_src.textChanged.connect(self._emit_data)
        self.icon_src.textChanged.connect(self._emit_data)
        self.button_bg_src.textChanged.connect(self._emit_data)
        self.align.currentIndexChanged.connect(self._emit_data)
        self.valign.currentIndexChanged.connect(self._emit_data)
        self.text_case.currentIndexChanged.connect(self._emit_data)
        self.text_multiline.textChanged.connect(self._emit_data)
        self.letter_spacing.valueChanged.connect(self._emit_data)
        self.line_height_pct.valueChanged.connect(self._emit_data)
        self.font_weight.currentIndexChanged.connect(self._emit_data)
        self.text_italic.toggled.connect(self._emit_data)
        self.text_underline.toggled.connect(self._emit_data)
        self.action_kind.currentIndexChanged.connect(self._on_action_kind_changed)
        self.action_screen.currentIndexChanged.connect(self._emit_data)

        self.btn_import_icon.clicked.connect(lambda: self._import_into_line(self.icon_src))
        self.btn_import_image.clicked.connect(lambda: self._import_into_line(self.image_src))
        self.btn_import_button_bg.clicked.connect(lambda: self._import_into_line(self.button_bg_src))

        self.setEnabled(False)

    def set_assets_dir(self, path: Path | None) -> None:
        self._assets_dir = path.resolve() if path else None
        ok = path is not None
        self.btn_import_icon.setEnabled(ok)
        self.btn_import_image.setEnabled(ok)
        self.btn_import_button_bg.setEnabled(ok)

    def _import_into_line(self, line: QLineEdit) -> None:
        if not self._assets_dir:
            QMessageBox.warning(self, "Нет папки assets", "Откройте проект, чтобы загружать файлы.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.svg *.ico);;Все файлы (*.*)",
        )
        if not path:
            return
        try:
            from touch_panel_studio.infrastructure.storage.asset_import import import_file_into_assets

            rel = import_file_into_assets(self._assets_dir, Path(path))
            self._block = True
            try:
                line.setText(rel)
            finally:
                self._block = False
            self._emit_data()
        except Exception as e:
            QMessageBox.critical(self, "Не удалось сохранить файл", str(e))

    def set_action_screens(self, screens: list[tuple[int, str]]) -> None:
        self._action_screens = list(screens)
        self._block = True
        try:
            self.action_screen.clear()
            for sid, label in screens:
                self.action_screen.addItem(label, int(sid))
        finally:
            self._block = False

    def set_state(self, state: InspectorFullState | None) -> None:
        self._block = True
        try:
            self._state = state
            if state is None:
                self._inspector_text_component_id = None
                self.setEnabled(False)
                return
            self.setEnabled(True)
            self.comp_type_label.setText(state.comp_type)
            self.name_edit.setText(state.name or "")

            self.x.setValue(state.x)
            self.y.setValue(state.y)
            self.w.setValue(state.width)
            self.h.setValue(state.height)
            self.z.setValue(state.z_index)
            self.visible.setChecked(bool(state.visible))

            st = dict(state.style)
            pr = dict(state.props)
            bd = dict(state.bindings)

            self.fill_edit.setText(str(st.get("fill", "")))
            self.stroke_edit.setText(str(st.get("stroke", "")))
            self.stroke_w.setValue(int(st.get("stroke_width", 1)))
            self.radius.setValue(int(st.get("radius", 0)))
            self.opacity.setValue(float(st.get("opacity", 1.0)))

            if state.comp_type == "text":
                self.text_stack.setCurrentWidget(self.text_multiline)
                new_t = str(pr.get("text", ""))
                same_component = self._inspector_text_component_id == state.component_id
                self._inspector_text_component_id = state.component_id
                if not same_component or self.text_multiline.toPlainText() != new_t:
                    self.text_multiline.setPlainText(new_t)
            else:
                self._inspector_text_component_id = None
                self.text_stack.setCurrentWidget(self.content_text)
                self.content_text.setText(str(pr.get("text", "")))
            if state.comp_type == "text":
                self.font_size.setValue(int(st.get("font_size", 24)))
            elif state.comp_type == "button":
                self.font_size.setValue(int(st.get("font_size", 20)))
            else:
                self.font_size.setValue(24)
            fam = str(st.get("font_family", "Segoe UI"))
            idx = self.font_family.findText(fam)
            if idx >= 0:
                self.font_family.setCurrentIndex(idx)
            else:
                self.font_family.setCurrentText(fam)
            if state.comp_type == "button":
                self.text_color.setText(str(st.get("color", "#ffffff")))
            else:
                self.text_color.setText(str(st.get("color", "#111111")))
            ix = self.align.findText(str(st.get("align", "left")))
            self.align.setCurrentIndex(max(0, ix))
            vdef = "center" if state.comp_type == "button" else "top"
            vraw = str(st.get("valign", "") or "").strip()
            vd = vraw if vraw in ("top", "center", "bottom") else vdef
            vix = self.valign.findData(vd)
            self.valign.setCurrentIndex(vix if vix >= 0 else 0)
            tc_raw = str(st.get("text_case", "none")).lower().strip()
            tc_ok = tc_raw if tc_raw in ("none", "upper", "lower", "first", "capitalize", "title") else "none"
            tc_ix = self.text_case.findData(tc_ok)
            self.text_case.setCurrentIndex(tc_ix if tc_ix >= 0 else 0)
            self.letter_spacing.setValue(int(round(float(st.get("letter_spacing_percent", 100)))))
            self.line_height_pct.setValue(int(round(float(st.get("line_height_percent", 120)))))
            fw = int(st.get("font_weight", 400))
            fwi = self.font_weight.findData(fw)
            self.font_weight.setCurrentIndex(fwi if fwi >= 0 else 0)
            self.text_italic.setChecked(bool(st.get("italic", False)))
            self.text_underline.setChecked(bool(st.get("underline", False)))
            self.image_src.setText(str(pr.get("src", "")))
            self.icon_src.setText(str(pr.get("icon_src", "")))
            self.button_bg_src.setText(str(pr.get("background_src", "")))

            ct = state.comp_type
            self.content_group.setVisible(ct in ("text", "button", "image"))
            self.text_stack.setVisible(ct in ("text", "button"))
            self.typo_group.setVisible(ct in ("text", "button"))
            self.icon_block.setVisible(ct == "button")
            self.button_bg_block.setVisible(ct == "button")
            self.image_block.setVisible(ct == "image")
            self.fill_edit.setVisible(ct in ("shape.rectangle", "shape.ellipse", "shape.line", "button", "image"))
            self.stroke_edit.setVisible(ct in ("shape.rectangle", "shape.ellipse", "shape.line", "button", "image"))
            self.stroke_w.setVisible(ct in ("shape.rectangle", "shape.ellipse", "shape.line", "button", "image"))
            self.radius.setVisible(ct in ("shape.rectangle", "shape.ellipse", "button", "image"))
            self.opacity.setVisible(True)

            oc = bd.get("on_click") if isinstance(bd.get("on_click"), dict) else {}
            t = str(oc.get("type", "none")).lower()
            ki = self.action_kind.findText(t)
            self.action_kind.setCurrentIndex(max(0, ki))
            self._sync_action_widgets()

            self.action_url.setText(str(oc.get("url", "")))
            tid = oc.get("target_screen_id")
            if tid is not None:
                idx = self.action_screen.findData(int(tid))
                if idx >= 0:
                    self.action_screen.setCurrentIndex(idx)
        finally:
            self._block = False

    def _on_action_kind_changed(self) -> None:
        self._sync_action_widgets()
        self._emit_data()

    def _sync_action_widgets(self) -> None:
        t = self.action_kind.currentText()
        self.action_screen.setVisible(t == "open_screen")
        self.action_url.setVisible(t == "open_url")

    def _emit_geometry(self) -> None:
        if self._block or self._state is None:
            return
        self.geometry_changed.emit(
            self._state.component_id,
            self.x.value(),
            self.y.value(),
            self.w.value(),
            self.h.value(),
        )

    def _emit_z(self) -> None:
        if self._block or self._state is None:
            return
        self.z_changed.emit(self._state.component_id, self.z.value())

    def _emit_visible(self, v: bool) -> None:
        if self._block or self._state is None:
            return
        self.visible_changed.emit(self._state.component_id, bool(v))

    def _emit_data(self) -> None:
        if self._block or self._state is None:
            return
        s = self._state
        props = dict(s.props)
        style = dict(s.style)
        ct = s.comp_type

        if ct == "text":
            props["text"] = self.text_multiline.toPlainText()
        elif ct == "button":
            props["text"] = self.content_text.text()
        if ct == "button":
            props["icon_src"] = self.icon_src.text().strip()
            props["background_src"] = self.button_bg_src.text().strip()
        if ct == "image":
            props["src"] = self.image_src.text().strip()

        op = float(self.opacity.value())
        if ct in ("shape.rectangle", "shape.ellipse", "shape.line", "button", "image"):
            # Пустое поле = без заливки / без обводки (не подставляем hex по умолчанию)
            style["fill"] = self.fill_edit.text().strip()
            style["stroke"] = self.stroke_edit.text().strip()
            style["stroke_width"] = int(self.stroke_w.value())
            style["radius"] = int(self.radius.value())
            style["opacity"] = op
        if ct == "text":
            style["color"] = self.text_color.text().strip() or "#111111"
            style["opacity"] = op
        if ct == "button":
            style["color"] = self.text_color.text().strip() or "#ffffff"
        if ct in ("text", "button"):
            style["font_size"] = int(self.font_size.value())
            style["font_family"] = self.font_family.currentText().strip() or "Segoe UI"
            style["align"] = self.align.currentText()
            vv = self.valign.currentData()
            style["valign"] = str(vv) if vv is not None else "top"
            tcase = self.text_case.currentData()
            style["text_case"] = str(tcase) if tcase is not None else "none"
            style["letter_spacing_percent"] = float(self.letter_spacing.value())
            style["line_height_percent"] = float(self.line_height_pct.value())
            wd = self.font_weight.currentData()
            style["font_weight"] = int(wd) if wd is not None else 400
            style["italic"] = bool(self.text_italic.isChecked())
            style["underline"] = bool(self.text_underline.isChecked())
            if ct == "text":
                style["opacity"] = op

        bindings: dict[str, Any] = {}
        ak = self.action_kind.currentText()
        oc: dict[str, Any] = {"type": ak}
        if ak == "open_screen" and self.action_screen.currentIndex() >= 0:
            sid = self.action_screen.currentData()
            if sid is not None:
                oc["target_screen_id"] = int(sid)
        if ak == "open_url":
            oc["url"] = self.action_url.text().strip()
        bindings["on_click"] = oc

        name = self.name_edit.text().strip()
        self.data_changed.emit(s.component_id, name, props, style, bindings)
