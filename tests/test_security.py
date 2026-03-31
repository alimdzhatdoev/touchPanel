from __future__ import annotations

import pytest

from touch_panel_studio.core.security import PasswordService


def test_password_hash_and_verify() -> None:
    svc = PasswordService.default()
    h = svc.hash_password("secret-password-123")
    assert h != "secret-password-123"
    assert svc.verify_password(h, "secret-password-123") is True
    assert svc.verify_password(h, "wrong") is False


def test_password_verify_invalid_hash_does_not_crash() -> None:
    svc = PasswordService.default()
    assert svc.verify_password("not-a-valid-argon2", "x") is False
