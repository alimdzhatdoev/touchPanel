from __future__ import annotations

import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from touch_panel_studio.db.base import Base
from touch_panel_studio.db.project_schema_migrations import apply_project_schema_migrations
from touch_panel_studio.db.session import SessionFactory
from touch_panel_studio.db.models.project import Project


_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


@dataclass(frozen=True, slots=True)
class ProjectMeta:
    name: str
    code: str
    description: str | None
    version: str
    created_at: str
    updated_at: str

    @staticmethod
    def now(name: str, code: str, description: str | None) -> "ProjectMeta":
        ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        return ProjectMeta(
            name=name,
            code=code,
            description=description,
            version="1.0.0",
            created_at=ts,
            updated_at=ts,
        )


class ProjectStorageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProjectHandle:
    root_dir: Path
    db_file: Path
    assets_dir: Path
    meta_file: Path
    meta: ProjectMeta

    def open_db(self) -> SessionFactory:
        sf = SessionFactory.for_sqlite_file(self.db_file)
        Base.metadata.create_all(bind=sf.engine)
        apply_project_schema_migrations(sf.engine)
        # Ensure single Project row exists (older projects might not have it).
        with sf.session() as s:
            existing_id = s.scalar(select(Project.id).limit(1))
            if existing_id is None:
                s.add(
                    Project(
                        name=self.meta.name,
                        code=self.meta.code,
                        description=self.meta.description,
                        version=self.meta.version,
                    )
                )
                s.commit()
        return sf


@dataclass(frozen=True, slots=True)
class ProjectStorage:
    projects_root: Path

    def ensure(self) -> None:
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[ProjectHandle]:
        self.ensure()
        items: list[ProjectHandle] = []
        for p in sorted(self.projects_root.iterdir(), key=lambda x: x.name.lower()):
            if not p.is_dir():
                continue
            meta_file = p / "project.json"
            if not meta_file.exists():
                continue
            try:
                meta = self._read_meta(meta_file)
            except Exception:
                continue
            items.append(self._handle_from_meta(p, meta))
        return items

    def create_project(self, name: str, code: str | None = None, description: str | None = None) -> ProjectHandle:
        self.ensure()
        name = name.strip()
        if len(name) < 2:
            raise ProjectStorageError("Название проекта слишком короткое.")

        if code is None or not code.strip():
            code = self._generate_code()
        code = code.strip().lower()
        if not _CODE_RE.match(code):
            raise ProjectStorageError("Код проекта должен быть 3–64 символа: a-z, 0-9, '_' или '-'.")

        root_dir = self.projects_root / code
        if root_dir.exists():
            raise ProjectStorageError("Проект с таким кодом уже существует.")

        tmp_dir = self.projects_root / f".creating_{code}_{uuid.uuid4().hex}"
        tmp_dir.mkdir(parents=True, exist_ok=False)
        try:
            assets_dir = tmp_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=False)
            db_file = tmp_dir / "project.sqlite3"
            meta_file = tmp_dir / "project.json"

            meta = ProjectMeta.now(name=name, code=code, description=description)
            self._write_meta(meta_file, meta)

            sf = SessionFactory.for_sqlite_file(db_file)
            Base.metadata.create_all(bind=sf.engine)
            # Seed "projects" table in project DB (single project per DB).
            with sf.session() as s:
                s.add(
                    Project(
                        name=meta.name,
                        code=meta.code,
                        description=meta.description,
                        version=meta.version,
                    )
                )
                s.commit()

            # Windows: закрыть пул соединений до переименования папки с SQLite.
            sf.engine.dispose()

            tmp_dir.replace(root_dir)
        except Exception as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise ProjectStorageError(str(e)) from e

        return self.open_project(code)

    def open_project(self, code: str) -> ProjectHandle:
        self.ensure()
        code = code.strip().lower()
        root_dir = self.projects_root / code
        if not root_dir.exists():
            raise ProjectStorageError("Проект не найден.")
        meta_file = root_dir / "project.json"
        if not meta_file.exists():
            raise ProjectStorageError("Повреждён проект: отсутствует project.json.")
        meta = self._read_meta(meta_file)
        return self._handle_from_meta(root_dir, meta)

    def delete_project(self, code: str, backup_to: Path) -> Path:
        handle = self.open_project(code)
        backup_to.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_path = backup_to / f"{handle.meta.code}_{ts}.zip"

        tmp_base = backup_to / f".tmp_zip_{handle.meta.code}_{uuid.uuid4().hex}"
        tmp_base.mkdir(parents=True, exist_ok=False)
        try:
            shutil.make_archive(str(tmp_base / handle.meta.code), "zip", root_dir=str(handle.root_dir))
            produced = (tmp_base / f"{handle.meta.code}.zip")
            produced.replace(archive_path)
        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)

        shutil.rmtree(handle.root_dir, ignore_errors=False)
        return archive_path

    def duplicate_project(self, code: str, new_code: str | None = None) -> ProjectHandle:
        src = self.open_project(code)
        if new_code is None or not new_code.strip():
            new_code = f"{src.meta.code}-{uuid.uuid4().hex[:6]}"
        new_code = new_code.strip().lower()
        if not _CODE_RE.match(new_code):
            raise ProjectStorageError("Новый код проекта некорректный.")

        dst_dir = self.projects_root / new_code
        if dst_dir.exists():
            raise ProjectStorageError("Проект с таким кодом уже существует.")

        tmp_dir = self.projects_root / f".duplicating_{new_code}_{uuid.uuid4().hex}"
        shutil.copytree(src.root_dir, tmp_dir)
        try:
            meta_file = tmp_dir / "project.json"
            meta = self._read_meta(meta_file)
            meta = ProjectMeta(
                name=f"{meta.name} (копия)",
                code=new_code,
                description=meta.description,
                version=meta.version,
                created_at=meta.created_at,
                updated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            )
            self._write_meta(meta_file, meta)
            tmp_dir.replace(dst_dir)
        except Exception as e:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise ProjectStorageError(str(e)) from e

        return self.open_project(new_code)

    def _generate_code(self) -> str:
        return f"proj-{uuid.uuid4().hex[:8]}"

    def _read_meta(self, meta_file: Path) -> ProjectMeta:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        return ProjectMeta(
            name=str(data["name"]),
            code=str(data["code"]),
            description=(str(data["description"]) if data.get("description") is not None else None),
            version=str(data.get("version", "1.0.0")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )

    def _write_meta(self, meta_file: Path, meta: ProjectMeta) -> None:
        meta_file.write_text(
            json.dumps(
                {
                    "name": meta.name,
                    "code": meta.code,
                    "description": meta.description,
                    "version": meta.version,
                    "created_at": meta.created_at,
                    "updated_at": meta.updated_at,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _handle_from_meta(self, root_dir: Path, meta: ProjectMeta) -> ProjectHandle:
        return ProjectHandle(
            root_dir=root_dir,
            db_file=root_dir / "project.sqlite3",
            assets_dir=root_dir / "assets",
            meta_file=root_dir / "project.json",
            meta=meta,
        )

