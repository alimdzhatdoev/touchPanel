"""Значения по умолчанию для компонентов экрана (props/style по типу)."""

from __future__ import annotations

from typing import Any


def default_name_for_type(comp_type: str) -> str:
    return {
        "shape.rectangle": "Прямоугольник",
        "shape.ellipse": "Эллипс",
        "shape.line": "Линия",
        "text": "Текст",
        "button": "Кнопка",
        "image": "Изображение",
    }.get(comp_type, "Элемент")


def default_props_for_type(comp_type: str) -> dict[str, Any]:
    t = (comp_type or "").lower()
    if t == "text":
        return {"text": "Текст"}
    if t == "button":
        return {"text": "Кнопка", "icon_src": "", "background_src": ""}
    if t == "image":
        return {"src": ""}
    return {}


def default_style_for_type(comp_type: str) -> dict[str, Any]:
    t = (comp_type or "").lower()
    base: dict[str, Any] = {
        "fill": "#ffffff",
        "stroke": "#333333",
        "stroke_width": 1,
        "radius": 0,
        "opacity": 1.0,
    }
    if t in ("shape.rectangle", "button"):
        base["radius"] = 4
    if t == "shape.ellipse":
        base["fill"] = "#e3f2fd"
    if t == "shape.line":
        base["fill"] = "transparent"
        base["stroke"] = "#333333"
        base["stroke_width"] = 4
        base["radius"] = 0
    if t == "text":
        return {
            "color": "#111111",
            "font_size": 24,
            "font_family": "Segoe UI",
            "align": "left",
            "valign": "top",
            "opacity": 1.0,
            "font_weight": 400,
            "italic": False,
            "underline": False,
            "letter_spacing_percent": 100,
            "line_height_percent": 120,
            "text_case": "none",
        }
    if t == "button":
        base["fill"] = "#1976d2"
        base["stroke"] = "#0d47a1"
        base["stroke_width"] = 1
        base["radius"] = 8
        return {
            **base,
            "font_size": 20,
            "font_family": "Segoe UI",
            "color": "#ffffff",
            "align": "center",
            "valign": "center",
            "font_weight": 400,
            "italic": False,
            "underline": False,
            "letter_spacing_percent": 100,
            "line_height_percent": 120,
            "text_case": "none",
        }
    if t == "image":
        return {
            "opacity": 1.0,
            "fill": "transparent",
            "stroke": "transparent",
            "stroke_width": 0,
            "radius": 0,
        }
    return base


def default_bindings() -> dict[str, Any]:
    return {"on_click": {"type": "none"}}
