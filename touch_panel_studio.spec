# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: onedir (основной вариант для Windows touch panels).
# Onefile: см. touch_panel_studio_onefile.spec

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

ROOT = Path(os.path.abspath(SPEC)).parent

# PySide6: подтянуть Qt DLL, плагины и зависимости
datas_pyside, binaries_pyside, hiddenimports_pyside = collect_all("PySide6")

_logo = ROOT / "appLogo.png"
_extra_datas = [(str(_logo), ".")] if _logo.is_file() else []

a = Analysis(
    [str(ROOT / "touch_panel_studio" / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries_pyside,
    datas=datas_pyside + _extra_datas,
    hiddenimports=hiddenimports_pyside
    + [
        "touch_panel_studio",
        "touch_panel_studio.db.models",
        "touch_panel_studio.db.migrations",
        "pydantic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="touch_panel_studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon: положите app.ico в корень репозитория и раскомментируйте:
    # icon=str(ROOT / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="touch_panel_studio",
)
