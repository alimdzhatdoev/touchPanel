from __future__ import annotations

import html
import json
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "docs" / "russian_patent"

# Сведения о программе берём только из проекта (без персональных данных).
PROGRAM = {
    "name": "Touch Panel Studio",
    "type": "Программа для ЭВМ",
    "purpose": (
        "Локальное автономное desktop‑приложение для Windows touch panels: "
        "редактор (Studio) и проигрыватель (Runtime) экранов/панелей."
    ),
    "functions": [
        "Создание и управление проектами (создать/дублировать/архивировать, импорт/экспорт).",
        "Редактор экранов: канвас, сетка, перемещение и изменение размеров компонентов.",
        "Компоненты: текст, кнопка, изображение, фигуры (прямоугольник/эллипс/линия).",
        "Настройка типографики (шрифт, размер, выравнивания по горизонтали/вертикали, регистр букв, межстрочный интервал).",
        "Runtime‑проигрыватель: отображение экранов и обработка действий по нажатию.",
        "Локальное хранение проектов и ресурсов в профиле пользователя Windows.",
    ],
    "platform": "Windows 10/11 x64",
    "language": "Python 3.x",
    "frameworks": ["PySide6 (Qt6)", "SQLAlchemy", "Alembic", "Pydantic"],
    "db": "SQLite (app.sqlite3 для пользователей/настроек и project.sqlite3 для данных проекта)",
    "ui": "Qt Widgets",
}


INVALID = re.compile(r'[<>:"/\\|?*]')


def safe_name(stem: str) -> str:
    s = INVALID.sub("_", stem)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Minimal DOCX writer (OOXML in zip).
CONTENT_TYPES = """<?xml version='1.0' encoding='UTF-8'?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

RELS = """<?xml version='1.0' encoding='UTF-8'?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""


def w_p(text: str) -> str:
    text = text or ""
    parts = text.split("\n")
    out = []
    for part in parts:
        t = html.escape(part)
        out.append(f'<w:p><w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>')
    return "".join(out)


def make_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(w_p(p) for p in paragraphs)
    doc = f"""<?xml version='1.0' encoding='UTF-8'?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr/>
  </w:body>
</w:document>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)


def classify(original: str) -> dict[str, bool]:
    low = original.lower()
    is_db = ("баз" in low and "дан" in low) or ("базы данных" in low)
    is_payment = ("платеж" in low) or ("поруч" in low) or ("оплат" in low)
    is_personal = ("персонал" in low) or ("персон" in low and "дан" in low)
    is_ref = "реферат" in low
    is_cover = ("сопров" in low) or ("сопровод" in low)
    is_stickers = ("наклей" in low) or ("диск" in low)
    is_title_pdf = ("титул" in low) and ("pdf" in low)
    return {
        "is_db": is_db,
        "is_payment": is_payment,
        "is_personal": is_personal,
        "is_ref": is_ref,
        "is_cover": is_cover,
        "is_stickers": is_stickers,
        "is_title_pdf": is_title_pdf,
    }


def program_ready_text() -> str:
    return (
        f"Название программы: {PROGRAM['name']}\n"
        f"Назначение: {PROGRAM['purpose']}\n\n"
        "Ключевые функции:\n- " + "\n- ".join(PROGRAM["functions"]) + "\n\n"
        f"Среда/ОС: {PROGRAM['platform']}\n"
        f"Язык программирования: {PROGRAM['language']}\n"
        f"Технологии: {', '.join(PROGRAM['frameworks'])}\n"
        f"Интерфейс: {PROGRAM['ui']}\n"
        f"Хранение данных: {PROGRAM['db']}\n"
    )


def build_helper_for(original_name: str) -> list[str]:
    info = classify(original_name)

    out: list[str] = []
    out.append("### 1. Исходный файл")
    out.append(f"Оригинал: {original_name}")

    out.append("### 2. Назначение документа")
    if info["is_ref"]:
        out.append("Реферат (аннотация/краткое описание объекта охраны) для подачи в Роспатент.")
    elif info["is_payment"]:
        out.append("Платёжный документ/поручение для уплаты пошлины.")
    elif info["is_personal"]:
        out.append("Согласие/сведения о персональных данных (образец).")
    elif info["is_cover"]:
        out.append("Сопроводительное письмо в Роспатент (обычно на фирменном бланке).")
    elif info["is_stickers"]:
        out.append("Наклейки/маркировка для диска/носителя (если подача на материальном носителе).")
    elif info["is_title_pdf"]:
        out.append("Титульный лист для PDF‑пакета документов (пример/шаблон).")
    else:
        out.append("Форма/страницы заявления/карточки для регистрации (по названию — шаблон формы).")

    out.append("### 3. Нужен ли он в нашем случае")
    if info["is_db"]:
        out.append("Нет, не нужен. Это относится к регистрации базы данных, а мы подаём только программу для ЭВМ.")
    elif info["is_stickers"]:
        out.append(
            "Нужен только при определенных условиях — если подача выполняется на материальном носителе "
            "(диск/флеш) и требуется маркировка."
        )
    elif info["is_title_pdf"]:
        out.append(
            "Нужен только при определенных условиях — если вы формируете единый PDF и этот титульный лист "
            "требуется по выбранному регламенту/шаблону подачи."
        )
    else:
        out.append("Да, нужен (для регистрации программы для ЭВМ).")

    out.append("### 4. Что именно нужно вписать в оригинальный файл")

    rows: list[str] = []

    def add(field: str, what: str, from_project: bool) -> None:
        rows.append(f"- {field}: {what} | из проекта: {'да' if from_project else 'нет'}")

    add("Название программы", PROGRAM["name"], True)
    add("Вид объекта", "Программа для ЭВМ", True)
    add("Назначение/краткое описание", "Краткое описание назначения и функций", True)
    add("Язык программирования", PROGRAM["language"], True)
    add("ОС/платформа", PROGRAM["platform"], True)

    if info["is_payment"]:
        add("Реквизиты плательщика/получателя, КБК, сумма", "заполняется вручную", False)
        add("Дата, номер платежного поручения", "заполняется вручную", False)
    if info["is_personal"]:
        add("ФИО автора(ов)/правообладателя", "заполняется вручную", False)
        add("Паспорт/адрес/телефон/эл.почта", "заполняется вручную", False)
        add("Подпись и дата", "заполняется вручную", False)
    if info["is_cover"]:
        add("Кому адресовано", "Роспатент (уточнить подразделение) — заполняется вручную", False)
        add("Исходящий номер/дата", "заполняется вручную", False)
        add("Перечень прилагаемых документов", "частично готовые формулировки ниже; состав — вручную", True)
    if info["is_ref"] and not info["is_db"]:
        add("Аннотация/реферат", "готовый текст ниже", True)
        add("Область применения", "заполняется вручную (или уточнить по проекту)", False)
    if info["is_stickers"]:
        add("Маркировка носителя", "Название программы, правообладатель, год, версия — часть вручную", True)

    out.extend(rows)

    out.append("### 5. Готовый текст или формулировки для вставки")
    if info["is_db"]:
        out.append("Этот файл относится к регистрации базы данных и в текущем кейсе не используется.")
    else:
        if info["is_ref"]:
            out.append("Реферат/аннотация (для программы для ЭВМ):")
            out.append(
                "Touch Panel Studio — автономное desktop‑приложение для Windows, предназначенное для проектирования "
                "и воспроизведения экранов touch‑панелей. Программа включает редактор (Studio) для создания проектов, "
                "экранов и UI‑компонентов, а также Runtime‑проигрыватель для запуска созданных экранов. Поддерживаются "
                "текстовые элементы, кнопки, изображения и базовые фигуры, настройка шрифтов и выравнивания, а также "
                "локальное хранение проектов и ресурсов."
            )
            out.append("Технические сведения:")
            out.append(program_ready_text())
        elif info["is_cover"]:
            out.append("Шаблон формулировки сопроводительного письма (без персональных данных):")
            out.append(
                "Просим принять документы для государственной регистрации программы для ЭВМ «Touch Panel Studio». "
                "В состав подачи входят заявление, реферат, материалы об объекте, а также документы, требуемые регламентом. "
                "Контактные данные и подписи: заполняется вручную."
            )
        elif info["is_stickers"]:
            out.append("Текст для наклеек (если требуется):")
            out.append(
                "Touch Panel Studio\n"
                "Тип: программа для ЭВМ\n"
                "Версия/год: заполняется вручную\n"
                "Правообладатель: заполняется вручную\n"
            )
        else:
            out.append("Сведения о программе (можно использовать в заявлении/описании):")
            out.append(program_ready_text())

    out.append("### 6. Что нельзя заполнять автоматически")
    out.append(
        "- ФИО, паспортные данные, адреса, телефоны, e-mail автора(ов)/правообладателя — заполняется вручную\n"
        "- Подписи и даты подписания — заполняется вручную\n"
        "- Реквизиты оплаты/платёжного поручения — заполняется вручную\n"
        "- Номера заявок/исходящие номера, если требуются — заполняется вручную"
    )

    out.append("### 7. Примечание")
    if info["is_db"]:
        out.append("Этот файл относится к регистрации базы данных и в текущем кейсе не используется.")
    else:
        out.append("Если какие-либо поля в оригинале требуют конкретных данных заявителя/правообладателя — заполняется вручную.")

    return out


def main() -> int:
    if not ROOT.exists():
        raise SystemExit(f"Folder not found: {ROOT}")

    originals = [p for p in sorted(ROOT.iterdir()) if p.is_file() and not p.name.lower().endswith("_информация_для_заполнения.docx")]
    created: list[str] = []
    for f in originals:
        out_name = f"{safe_name(f.stem)}_информация_для_заполнения.docx"
        out_path = ROOT / out_name
        make_docx(out_path, build_helper_for(f.name))
        created.append(out_name)

    print(json.dumps({"created": created}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

