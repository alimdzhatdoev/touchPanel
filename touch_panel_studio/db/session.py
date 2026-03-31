from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def sqlite_engine(db_file: Path) -> Engine:
    db_file.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite+pysqlite:///{db_file.as_posix()}"
    engine = create_engine(
        url,
        future=True,
        connect_args={"check_same_thread": False},
    )
    return engine


@dataclass(frozen=True, slots=True)
class SessionFactory:
    engine: Engine
    _maker: sessionmaker

    @staticmethod
    def for_sqlite_file(db_file: Path) -> "SessionFactory":
        engine = sqlite_engine(db_file)
        maker = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, expire_on_commit=False)
        return SessionFactory(engine=engine, _maker=maker)

    def session(self) -> Session:
        return self._maker()

