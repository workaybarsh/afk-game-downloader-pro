@echo off
rem Build the setup wizard, bundling the application and the uninstaller inside it.
cd /d "%~dp0"

if not exist "dist\AFK Game Downloader Pro.exe" (
  echo Application exe not found, building it first...
  call build_exe.bat || goto :error
)
if not exist "dist\AFK Game Downloader Pro Uninstall.exe" (
  echo Uninstaller not found, building it first...
  call build_uninstaller.bat || goto :error
)

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
echo Done: dist\AFK Game Downloader Pro Setup.exe
exit /b 0

:error
echo.
echo Build failed. Install PyInstaller first:  python -m pip install pyinstaller
pause
exit /b 1
