@echo off
setlocal
cd /d "%~dp0"

echo [1/2] Installing PyInstaller if needed...
python -m pip install -q "pyinstaller>=6.6.0"

echo.
echo Building onedir (recommended): dist\touch_panel_studio\
pyinstaller --noconfirm touch_panel_studio.spec
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo.
echo Done. Run: dist\touch_panel_studio\touch_panel_studio.exe
echo Optional onefile: pyinstaller --noconfirm touch_panel_studio_onefile.spec
exit /b 0
