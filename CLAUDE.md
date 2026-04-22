# CLAUDE.md

## Работа с кодом

- Чистый, читаемый, эффективный и поддерживаемый код
- Без оверинжиниринга и лишних абстракций
- Только функциональные компоненты (для React)
- Компоненты маленькие — одна ответственность
- Логика в хуках/утилитах, UI отдельно
- Понятные и единообразные названия
- Перед созданием нового компонента проверь нет ли похожего
- Не дублировать логику — переиспользовать
- Не вносить новые зависимости без явной необходимости
- Всегда анализируй существующую структуру и стиль проекта перед тем как писать код
- Строго следуй архитектуре и паттернам которые уже используются в проекте

## Визуальный стиль

**Если проект уже существует:**
- Проанализируй существующие компоненты, цвета, шрифты, отступы и паттерны
- Строго следуй этой стилистике во всех новых элементах
- Не вноси визуальные изменения если не просят

**Если проект новый:**
- Найди в интернете как выглядят современные сайты или приложения в этой тематике
- Изучи какие цвета, типографику и UI-паттерны используют лидеры в этой нише
- Подбери уникальную палитру под тематику — не шаблонные синий/серый
- Один цвет доминирует (60-70%), один поддерживающий, один акцентный
- Современный дизайн: чистые линии, достаточно воздуха, чёткая иерархия
- Не делай скучно — каждый экран должен выглядеть продуманно и красиво

## Экономия токенов

- Не объясняй что делаешь — просто делай
- Без лишних комментариев и резюме после выполнения
- Если задача понятна — не переспрашивай
- Думай на английском, отвечай на русском

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Touch Panel Studio** — a Windows desktop application (PySide6/Python) for designing and running touch panel interfaces. It has two modes:
- **Admin Studio**: WYSIWYG editor for designing screens and components
- **Runtime Player**: Player for running designed projects

Default credentials: `admin` / `admin`

## Commands

**Run the app:**
```bash
python -m touch_panel_studio.app.main
# or simply:
run.bat   # auto-creates venv, installs deps, then launches
```

**Build .exe (onedir, preferred):**
```bash
build.bat
# or manually:
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean touch_panel_studio.spec
```

**Run tests:**
```bash
pytest
```

**Lint / format:**
```bash
ruff check .
black .
```

**Database migrations (global app DB):**
```bash
alembic upgrade head
```

## Architecture

The app follows a layered clean architecture:

```
touch_panel_studio/
├── app/          # Orchestration: entry point, DI bootstrap, app state machine
├── core/         # Infrastructure: config, paths, logging, security, constants
├── domain/       # Business logic: component presets, enums (UserRole)
├── db/           # SQLAlchemy ORM: models, repositories, Alembic migrations
├── infrastructure/ # Services: auth, project storage, asset handling, import/export
└── ui/           # PySide6 GUI: windows, editor canvas, runtime renderer, widgets
```

### Key flow

1. `app/main.py` → creates `QApplication`, runs `bootstrap.py` (DB init, default admin creation)
2. `app/controller.py` — central state machine driving transitions: Splash → Login → ProjectManager → Studio or Runtime
3. `app/context.py` — `AppContext` acts as the dependency injection container (holds session factory, services, current user)

### Data storage (Windows AppData)

- **Global DB**: `%LOCALAPPDATA%\TouchPanelStudio\runtime\app.sqlite3` — users, global settings, template cache
- **Per-project DB**: `%LOCALAPPDATA%\TouchPanelStudio\projects\<project_code>\project.sqlite3` — screens, components, actions, revisions
- **Assets**: `%LOCALAPPDATA%\TouchPanelStudio\projects\<project_code>\assets\`

### UI layer structure

- `ui/windows/` — top-level windows and dialogs (login, project manager, studio, user admin)
- `ui/editor/` — canvas editor with drag/drop (`canvas_editor.py`, `grid_scene.py`), property inspector, graphics items in `items/`
- `ui/runtime/` — runtime player: renderer, mirror widgets, scaled screen
- UI communicates back to `AppController` via Qt signals/slots

### Infrastructure services

- `infrastructure/auth/auth_service.py` — authentication (argon2 hashing via `core/security.py`)
- `infrastructure/storage/project_storage.py` — project CRUD, creates per-project SQLite databases
- `infrastructure/import_export/` — project archive export/import with schema migration (`migrator.py`) and validation (`validator.py`), Pydantic schemas in `schemas.py`
- `infrastructure/storage/asset_import.py` — image/asset import pipeline

### Domain

- `domain/component_presets.py` — defines available component types (text, button, image, shapes) with their default property templates
- `domain/enums/roles.py` — `UserRole` enum

## Tech stack

| Concern | Library |
|---------|---------|
| GUI | PySide6 (Qt6) |
| ORM | SQLAlchemy 2.x |
| DB migrations | Alembic |
| Validation/schemas | Pydantic v2 |
| Password hashing | argon2-cffi |
| Packaging | PyInstaller (`.spec` files in repo root) |
| Tests | pytest |
| Formatter | black |
| Linter | ruff |

## Notes

- UI text, README, and most comments are in **Russian**.
- The project targets **Windows only** — paths use `%LOCALAPPDATA%` via `core/paths.py`.
- Per-project schema migrations on import are handled separately from Alembic (see `db/project_schema_migrations.py`).
- `pytest.ini` sets `testpaths=tests` and suppresses specific Qt deprecation warnings.
