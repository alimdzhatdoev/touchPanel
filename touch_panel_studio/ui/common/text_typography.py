"""Общие настройки шрифта и многострочного текста для редактора и runtime."""

from __future__ import annotations

import string as string_std

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QColor,
    QFont,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextOption,
)


def font_from_text_style(style: dict, *, default_size: int, default_family: str) -> QFont:
    fam = str(style.get("font_family", default_family))
    fs = max(6, int(style.get("font_size", default_size)))
    f = QFont(fam, fs)
    fw = int(style.get("font_weight", 400))
    fw = max(100, min(900, fw))
    try:
        f.setWeight(QFont.Weight(fw))
    except (TypeError, ValueError):
        f.setWeight(QFont.Weight.Normal)
    f.setItalic(bool(style.get("italic", False)))
    f.setUnderline(bool(style.get("underline", False)))
    lp = float(style.get("letter_spacing_percent", 100))
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, max(10.0, min(400.0, lp)))
    return f


def apply_text_case(text: str, mode: object | None) -> str:
    """Регистр для отображения (редактор, runtime). В props хранится исходная строка."""
    m = str(mode or "none").lower().strip()
    if m in ("", "none", "normal"):
        return text
    if m == "upper":
        return text.upper()
    if m == "lower":
        return text.lower()
    if m == "capitalize":
        return _capitalize_first_per_line(text)
    if m == "first":
        if not text:
            return text
        return text[0].upper() + text[1:].lower()
    if m == "title":
        return "\n".join(string_std.capwords(line) for line in text.split("\n"))
    return text


def _capitalize_first_per_line(s: str) -> str:
    def one(line: str) -> str:
        if not line:
            return line
        return line[0].upper() + line[1:].lower()

    return "\n".join(one(line) for line in s.split("\n"))


def apply_line_height_to_document(doc: QTextDocument, line_height_percent: float) -> None:
    # PySide6: setLineHeight(height: float, heightType: int); enum → .value
    lh = float(max(50, min(400, round(line_height_percent))))
    height_type = QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
    b = doc.firstBlock()
    while b.isValid():
        cur = QTextCursor(b)
        bf = QTextBlockFormat()
        bf.setLineHeight(lh, height_type)
        cur.mergeBlockFormat(bf)
        b = b.next()


def _valign_key(style: dict, *, default: str = "top") -> str:
    raw = style.get("valign")
    if raw is None or str(raw).strip() == "":
        v = default
    else:
        v = str(raw).lower().strip()
    if v in ("middle", "vcenter"):
        return "center"
    return v if v in ("top", "center", "bottom") else default


def _vertical_alignment_flag(valign: str) -> Qt.AlignmentFlag:
    if valign == "center":
        return Qt.AlignmentFlag.AlignVCenter
    if valign == "bottom":
        return Qt.AlignmentFlag.AlignBottom
    return Qt.AlignmentFlag.AlignTop


def qlabel_alignment_flags(style: dict, *, valign_default: str | None = None) -> Qt.AlignmentFlag:
    """Горизонталь (align) + вертикаль (valign) + перенос слов для QLabel."""
    align = str(style.get("align", "left")).lower()
    if align == "center":
        ha = Qt.AlignmentFlag.AlignHCenter
    elif align == "right":
        ha = Qt.AlignmentFlag.AlignRight
    else:
        ha = Qt.AlignmentFlag.AlignLeft
    vd = valign_default if valign_default is not None else "top"
    valign = _valign_key(style, default=vd)
    va = _vertical_alignment_flag(valign)
    return ha | va | Qt.AlignmentFlag.TextWordWrap


def paint_styled_text_block(
    painter,
    rect: QRectF,
    text: str,
    *,
    style: dict,
    default_size: int,
    default_family: str,
    valign_default: str | None = None,
) -> None:
    """Рисует многострочный текст с переносами, межстрочным интервалом и выравниванием."""
    text = apply_text_case(text, style.get("text_case"))
    font = font_from_text_style(style, default_size=default_size, default_family=default_family)
    color = QColor(str(style.get("color", "#111111")))
    align = str(style.get("align", "left")).lower()
    if align == "center":
        ha = Qt.AlignmentFlag.AlignHCenter
    elif align == "right":
        ha = Qt.AlignmentFlag.AlignRight
    else:
        ha = Qt.AlignmentFlag.AlignLeft

    valign = _valign_key(style, default=(valign_default if valign_default is not None else "top"))
    va = _vertical_alignment_flag(valign)

    doc = QTextDocument()
    doc.setDefaultFont(font)
    doc.setPlainText(text)
    doc.setTextWidth(rect.width())

    opt = QTextOption()
    opt.setAlignment(ha | va)
    opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    doc.setDefaultTextOption(opt)

    lh = float(style.get("line_height_percent", 120))
    apply_line_height_to_document(doc, lh)

    cur = QTextCursor(doc)
    cur.select(QTextCursor.SelectionType.Document)
    cf = QTextCharFormat()
    cf.setForeground(color)
    cur.mergeCharFormat(cf)

    doc_h = float(doc.size().height())
    dy = 0.0
    if valign == "center":
        dy = max(0.0, (float(rect.height()) - doc_h) / 2.0)
    elif valign == "bottom":
        dy = max(0.0, float(rect.height()) - doc_h)

    painter.save()
    painter.setClipRect(rect.toRect())
    painter.translate(rect.left(), rect.top() + dy)
    doc.drawContents(painter)
    painter.restore()


def qlabel_typography_stylesheet(style: dict, *, color: str) -> str:
    """Доп. CSS для QLabel (межстрочный интервал; цвет). Шрифт — через setFont."""
    lh = float(style.get("line_height_percent", 120))
    lh = max(80, min(250, lh))
    return f"color: {color}; background: transparent; line-height: {lh}%;"


def qpushbutton_typography_stylesheet(style: dict, *, color: str) -> str:
    lh = float(style.get("line_height_percent", 120))
    lh = max(80, min(250, lh))
    v = _valign_key(style, default="center")
    # QPushButton не умеет valign текста; грубая подстройка отступами
    if v == "top":
        pad = "padding: 4px 12px 12px 12px;"
    elif v == "bottom":
        pad = "padding: 12px 12px 4px 12px;"
    else:
        pad = "padding: 8px 12px;"
    return f"color: {color}; line-height: {lh}%; {pad}"
