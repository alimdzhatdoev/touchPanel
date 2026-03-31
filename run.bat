@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYEXE=%CD%\.venv\Scripts\python.exe"

if not exist "%PYEXE%" goto create_venv
goto ensure_deps

:create_venv
echo.
echo [Touch Panel Studio] Создаю .venv ...
echo.

py -m venv .venv 2>nul
if exist "%PYEXE%" goto install_deps

python -m venv .venv 2>nul
if exist "%PYEXE%" goto install_deps

echo ERROR: Python не найден или не удалось создать .venv
echo.
echo Установите Python 3.10+ x64: https://www.python.org/downloads/windows/
echo В установщике включите: "Add python.exe to PATH"
echo Затем снова запустите этот файл.
echo.
pause
exit /b 1

:ensure_deps
REM Если .venv есть, но пакеты не ставились / ставились в другой Python — доустановим
"%PYEXE%" -c "import PySide6" 2>nul
if errorlevel 1 goto install_deps
goto run_app

:install_deps
echo [Touch Panel Studio] Устанавливаю зависимости из requirements.txt ...
echo (первый раз может занять 1-3 минуты^)
"%PYEXE%" -m pip install -U pip
if errorlevel 1 goto pip_fail
"%PYEXE%" -m pip install -r "%CD%\requirements.txt"
if errorlevel 1 goto pip_fail
echo.

:run_app
echo [Touch Panel Studio] Запуск...
"%PYEXE%" -m touch_panel_studio.app.main
if errorlevel 1 (
  echo.
  echo Ошибка запуска. Код: %errorlevel%
  pause
)
exit /b %errorlevel%

:pip_fail
echo.
echo ОШИБКА: pip не смог установить пакеты.
echo Проверьте интернет, отключите блокировку pip в антивирусе, запустите от имени пользователя с правами на папку проекта.
pause
exit /b 1
