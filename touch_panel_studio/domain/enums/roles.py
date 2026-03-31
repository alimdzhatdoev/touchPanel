from __future__ import annotations

from enum import Enum

try:
    from enum import StrEnum  # py>=3.11
except ImportError:  # pragma: no cover (py<3.11 runtime)
    class StrEnum(str, Enum):  # type: ignore[misc]
        pass


class UserRole(StrEnum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"
    service = "service"

