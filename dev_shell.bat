@echo off
REM Открывает cmd с активированным .venv в папке проекта (удобно для ручных команд).
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Сначала запустите run.bat один раз — он создаст .venv
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
cmd /k "cd /d %CD%"
