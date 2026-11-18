@echo off
rem Build the application .exe (no Python needed on the target machine).
cd /d "%~dp0"
if not exist "assets\app.ico" (
  echo Building the icon first...
  python tools\make_icon.py || goto :error
)
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name "AFK Game Downloader Pro" ^
  --icon "assets\app.ico" ^
  --add-data "assets;assets" ^
  main.pyw
if errorlevel 1 goto :error
echo.
echo Done: dist\AFK Game Downloader Pro.exe
exit /b 0

:error
echo.
echo Build failed. Install PyInstaller first:  python -m pip install pyinstaller
pause
exit /b 1
