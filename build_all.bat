@echo off
rem Build everything: app exe, uninstall wizard, setup wizard (with both bundled).
cd /d "%~dp0"

if not exist "assets\app.ico" (
  echo Building the icon first...
  python tools\make_icon.py || goto :error
)

call build_exe.bat || goto :error
call build_uninstaller.bat || goto :error

python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name "AFK Game Downloader Pro Setup" ^
  --icon "assets\app.ico" ^
  --add-data "dist\AFK Game Downloader Pro.exe;payload" ^
  --add-data "dist\AFK Game Downloader Pro Uninstall.exe;payload" ^
  --add-data "LICENSE;." ^
  --add-data "assets;assets" ^
  installer.pyw
if errorlevel 1 goto :error

echo.
echo All builds done:
echo   dist\AFK Game Downloader Pro.exe
echo   dist\AFK Game Downloader Pro Uninstall.exe
echo   dist\AFK Game Downloader Pro Setup.exe
exit /b 0

:error
echo.
echo Build failed.
pause
exit /b 1
