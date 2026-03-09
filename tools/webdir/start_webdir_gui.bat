@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py gui.py
) else (
  python gui.py
)
echo.
echo WebDir exited. Press any key to close...
pause >nul

