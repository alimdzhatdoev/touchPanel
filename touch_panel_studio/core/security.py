from __future__ import annotations

from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


@dataclass(frozen=True, slots=True)
class PasswordService:
    _hasher: PasswordHasher

    @staticmethod
    def default() -> "PasswordService":
        return PasswordService(_hasher=PasswordHasher())

    def hash_password(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

