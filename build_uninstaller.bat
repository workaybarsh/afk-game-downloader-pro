@echo off
rem Build the standalone uninstall wizard.
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name "AFK Game Downloader Pro Uninstall" ^
  --icon "assets\app.ico" ^
  --add-data "assets;assets" ^
  uninstaller.pyw
if errorlevel 1 goto :error
echo.
echo Done: dist\AFK Game Downloader Pro Uninstall.exe
exit /b 0

:error
echo.
echo Build failed. Install PyInstaller first:  python -m pip install pyinstaller
pause
exit /b 1
