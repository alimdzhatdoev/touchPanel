"""«Запомнить меня»: логин + пароль на 24 ч, пароль через Windows DPAPI (только Windows)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

_FILENAME = "remember_login.json"

# 24 часа
TTL_SEC = 24 * 60 * 60


def _dpapi_protect(plain: bytes) -> bytes:
    if sys.platform != "win32":
        raise OSError("DPAPI только для Windows")
    import ctypes
    from ctypes import wintypes

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    CryptProtectData = crypt32.CryptProtectData
    CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    CryptProtectData.restype = wintypes.BOOL

    LocalFree = kernel32.LocalFree
    LocalFree.argtypes = [ctypes.c_void_p]
    LocalFree.restype = ctypes.c_void_p

    buf = (ctypes.c_byte * len(plain))(*plain)
    blob_in = DATA_BLOB(len(plain), ctypes.cast(ctypes.byref(buf), ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    if not CryptProtectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        if blob_out.pbData:
            LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))
    return bytes(out)


def _dpapi_unprotect(blob: bytes) -> bytes:
    if sys.platform != "win32":
        raise OSError("DPAPI только для Windows")
    import ctypes
    from ctypes import wintypes

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    CryptUnprotectData = crypt32.CryptUnprotectData
    CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    CryptUnprotectData.restype = wintypes.BOOL

    LocalFree = kernel32.LocalFree
    LocalFree.argtypes = [ctypes.c_void_p]
    LocalFree.restype = ctypes.c_void_p

    buf = (ctypes.c_byte * len(blob))(*blob)
    blob_in = DATA_BLOB(len(blob), ctypes.cast(ctypes.byref(buf), ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    if not CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        if blob_out.pbData:
            LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))
    return bytes(out)


def _path(config_dir: Path) -> Path:
    return config_dir / _FILENAME


def save(config_dir: Path, username: str, password: str) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        # Нет DPAPI — не храним пароль в открытом виде
        return
    try:
        enc = _dpapi_protect(password.encode("utf-8"))
    except OSError:
        return
    data: dict[str, Any] = {
        "v": 1,
        "exp": int(time.time()) + TTL_SEC,
        "u": username,
        "p": enc.hex(),
    }
    _path(config_dir).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load(config_dir: Path) -> tuple[str, str] | None:
    p = _path(config_dir)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        clear(config_dir)
        return None
    exp = int(data.get("exp", 0))
    if int(time.time()) > exp:
        clear(config_dir)
        return None
    u = str(data.get("u", "")).strip()
    ph = str(data.get("p", "")).strip()
    if not u or not ph or sys.platform != "win32":
        return None
    try:
        raw = bytes.fromhex(ph)
        pw = _dpapi_unprotect(raw).decode("utf-8")
    except (OSError, ValueError, UnicodeError):
        clear(config_dir)
        return None
    return u, pw


def clear(config_dir: Path) -> None:
    p = _path(config_dir)
    try:
        p.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass
