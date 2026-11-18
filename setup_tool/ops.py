"""Install / uninstall operations for the setup wizard."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import winreg
from pathlib import Path

APP_NAME = "AFK Game Downloader Pro"
APP_EXE = f"{APP_NAME}.exe"
UNINSTALLER_EXE = f"{APP_NAME} Uninstall.exe"
APP_VERSION = "1.0.0"
PUBLISHER = "AFK Game Downloader Pro"

RUN_VALUE = "AFKGameDownloaderPro"
UNINSTALL_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AFKGameDownloaderPro"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

CSIDL_DESKTOPDIRECTORY = 0x0010
CSIDL_PROGRAMS = 0x0002
CSIDL_LOCAL_APPDATA = 0x001C

CREATE_NO_WINDOW = 0x08000000


# --------------------------------------------------------------------- folders
def _known_folder(csidl: int, fallback: Path) -> Path:
    try:
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) == 0 and buf.value:
            return Path(buf.value)
    except Exception:  # noqa: BLE001
        pass
    return fallback


def desktop_dir() -> Path:
    return _known_folder(CSIDL_DESKTOPDIRECTORY, Path.home() / "Desktop")


def start_menu_dir() -> Path:
    fallback = Path(os.environ.get("APPDATA", Path.home())) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return _known_folder(CSIDL_PROGRAMS, fallback)


def local_appdata() -> Path:
    fallback = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return _known_folder(CSIDL_LOCAL_APPDATA, fallback)


def default_install_dir() -> Path:
    return local_appdata() / "Programs" / APP_NAME


# --------------------------------------------------------------------- payload
def payload_exe() -> Path:
    """The application executable bundled inside the installer."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates += [meipass / "payload" / APP_EXE, meipass / APP_EXE]
    root = Path(__file__).resolve().parent.parent
    candidates += [
        root / "payload" / APP_EXE,
        root / "dist" / APP_EXE,
        root / APP_EXE,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(APP_EXE)


def write_language(code: str) -> None:
    """Remember the chosen language for the application (merges the config)."""
    path = Path(os.environ.get("APPDATA", Path.home())) / "AFKGameDownloaderPro" / "config.json"
    data: dict = {}
    try:
        if path.is_file():
            loaded = json.loads(path.read_text("utf-8"))
            if isinstance(loaded, dict):
                data = loaded
    except (OSError, ValueError):
        data = {}
    data["language"] = code
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except OSError:
        pass


def installed_dir() -> Path:
    """Folder the running uninstaller lives in (frozen: next to the exe)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def uninstaller_payload() -> Path | None:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.append(meipass / "payload" / UNINSTALLER_EXE)
    root = Path(__file__).resolve().parent.parent
    candidates += [root / "payload" / UNINSTALLER_EXE, root / "dist" / UNINSTALLER_EXE]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def license_text() -> str:
    """Bundled MIT license text."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(getattr(sys, "_MEIPASS", "")) / "LICENSE")
    candidates.append(Path(__file__).resolve().parent.parent / "LICENSE")
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate.read_text("utf-8")
        except OSError:
            continue
    return "MIT License - see https://opensource.org/license/mit"


def asset_path(name: str) -> Path | None:
    bases: list[Path] = []
    if getattr(sys, "frozen", False):
        bases.append(Path(getattr(sys, "_MEIPASS", "")) / "assets")
    bases.append(Path(__file__).resolve().parent.parent / "assets")
    for base in bases:
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


# --------------------------------------------------------------------- process
def app_running() -> bool:
    try:
        from afkdl.procs import find_processes

        return bool(find_processes({APP_EXE}))
    except Exception:  # noqa: BLE001
        return False


def close_app() -> None:
    try:
        subprocess.run(
            ["taskkill", "/IM", APP_EXE, "/F"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=15,
        )
        time.sleep(1.0)
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------- shortcuts
def make_shortcut(link: Path, target: Path, workdir: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    script = (
        '$s = (New-Object -ComObject WScript.Shell).CreateShortcut("{link}");'
        '$s.TargetPath = "{target}";'
        '$s.WorkingDirectory = "{workdir}";'
        '$s.IconLocation = "{target},0";'
        '$s.Description = "{desc}";'
        '$s.Save()'
    ).format(link=link, target=target, workdir=workdir, desc=APP_NAME)
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
        timeout=60,
    )


def desktop_shortcut() -> Path:
    return desktop_dir() / f"{APP_NAME}.lnk"


def startmenu_shortcut() -> Path:
    return start_menu_dir() / f"{APP_NAME}.lnk"


# --------------------------------------------------------------------- registry
def register_uninstall(target: Path, exe: Path, uninstaller: Path) -> None:
    size_kb = 0
    try:
        size_kb = int(exe.stat().st_size / 1024)
    except OSError:
        pass
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
        values = {
            "DisplayName": (winreg.REG_SZ, APP_NAME),
            "DisplayVersion": (winreg.REG_SZ, APP_VERSION),
            "Publisher": (winreg.REG_SZ, PUBLISHER),
            "InstallLocation": (winreg.REG_SZ, str(target)),
            "DisplayIcon": (winreg.REG_SZ, f"{exe},0"),
            "UninstallString": (winreg.REG_SZ, f'"{uninstaller}"'),
            "QuietUninstallString": (winreg.REG_SZ, f'cmd /c ""{uninstaller}"" /quiet'),
            "EstimatedSize": (winreg.REG_DWORD, size_kb),
            "NoModify": (winreg.REG_DWORD, 1),
            "NoRepair": (winreg.REG_DWORD, 1),
        }
        for name, (kind, value) in values.items():
            winreg.SetValueEx(key, name, 0, kind, value)


# --------------------------------------------------------------------- uninstaller
def _ps_literal(text: str) -> str:
    return text.replace("'", "''")


def write_uninstaller(target: Path, exe: Path) -> Path:
    path = target / "Uninstall.cmd"
    path.write_text(
        "@echo off\r\n"
        "title AFK Game Downloader Pro - Uninstall\r\n"
        "setlocal\r\n"
        "if /i \"%~1\"==\"/quiet\" goto run\r\n"
        "echo.\r\n"
        f'echo   AFK Game Downloader Pro will be removed from:\r\n'
        f"echo     {target}\r\n"
        "echo.\r\n"
        'choice /c YN /n /m "  Continue? [Y/N] "\r\n'
        "if errorlevel 2 goto cancel\r\n"
        ":run\r\n"
        "echo.\r\n"
        "echo   Closing the app...\r\n"
        f'taskkill /IM "{APP_EXE}" /F >nul 2>&1\r\n'
        "echo   Removing shortcuts...\r\n"
        f'del /f /q "{desktop_shortcut()}" >nul 2>&1\r\n'
        f'del /f /q "{startmenu_shortcut()}" >nul 2>&1\r\n'
        "echo   Removing registry entries...\r\n"
        f'reg delete "HKCU\\{UNINSTALL_SUBKEY}" /f >nul 2>&1\r\n'
        f'reg delete "HKCU\\{RUN_KEY}" /v "{RUN_VALUE}" /f >nul 2>&1\r\n'
        "echo   Removing settings...\r\n"
        'rmdir /s /q "%APPDATA%\\AFKGameDownloaderPro" >nul 2>&1\r\n'
        "echo   Removing program files...\r\n"
        'start "" powershell -NoProfile -WindowStyle Hidden -Command "'
        f'Start-Sleep -Seconds 2; Remove-Item -LiteralPath \'{_ps_literal(str(target))}\' -Recurse -Force -ErrorAction SilentlyContinue"\r\n'
        "exit /b 0\r\n"
        "\r\n"
        ":cancel\r\n"
        "exit /b 1\r\n",
        encoding="utf-8",
        newline="",
    )
    return path


# --------------------------------------------------------------------- install
def validate_target(target: Path) -> tuple[bool, str]:
    """Return (ok, reason_key)."""
    try:
        resolved = target.expanduser().resolve()
    except OSError:
        return False, "setup.err_system"
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve()
    if resolved == windows or windows in resolved.parents:
        return False, "setup.err_system"
    if resolved.parent == resolved:  # drive root
        return False, "setup.err_system"
    return True, ""


def free_space(target: Path) -> int:
    probe = target
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        return shutil.disk_usage(probe).free
    except OSError:
        return 0


def install_uninstaller(target: Path, exe: Path) -> Path:
    """Copy the GUI uninstaller next to the app (falls back to the .cmd script)."""
    payload = uninstaller_payload()
    if payload:
        destination = target / UNINSTALLER_EXE
        shutil.copy2(payload, destination)
        try:
            (target / "Uninstall.cmd").unlink()
        except OSError:
            pass
        return destination
    return write_uninstaller(target, exe)


def _delete_registry_value(subkey: str, name: str) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
    except OSError:
        pass


def _delete_registry_key(subkey: str) -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)
    except OSError:
        pass


def schedule_folder_removal(target: Path, delay: int = 3) -> None:
    """Delete the install folder after this process has exited."""
    script = (
        f"Start-Sleep -Seconds {delay}; "
        f"Remove-Item -LiteralPath '{_ps_literal(str(target))}' -Recurse -Force -ErrorAction SilentlyContinue"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
        creationflags=CREATE_NO_WINDOW,
        close_fds=True,
    )


def uninstall_all(
    target: Path,
    remove_settings: bool = True,
    progress=lambda percent, key: None,
) -> None:
    """Remove the app, its shortcuts, registry entries and (optionally) settings."""
    progress(8, "uninstall.msg_stop")
    close_app()

    progress(28, "uninstall.msg_shortcuts")
    for link in (desktop_shortcut(), startmenu_shortcut()):
        try:
            link.unlink()
        except OSError:
            pass

    progress(46, "uninstall.msg_registry")
    _delete_registry_value(RUN_KEY, RUN_VALUE)
    _delete_registry_key(UNINSTALL_SUBKEY)

    progress(64, "uninstall.msg_settings")
    if remove_settings:
        settings = Path(os.environ.get("APPDATA", Path.home())) / "AFKGameDownloaderPro"
        shutil.rmtree(settings, ignore_errors=True)

    progress(82, "uninstall.msg_files")
    schedule_folder_removal(target)

    progress(100, "uninstall.msg_done")


def install(target: Path, options: dict, progress=lambda percent, key: None) -> None:
    source = payload_exe()
    needed = source.stat().st_size * 2 + 5 * 1024 * 1024

    progress(3, "setup.msg_prepare")
    target.mkdir(parents=True, exist_ok=True)
    if app_running():
        close_app()

    if free_space(target) < needed:
        raise OSError("setup.err_space")

    progress(20, "setup.msg_copy")
    destination = target / APP_EXE
    shutil.copy2(source, destination)

    progress(45, "setup.msg_shortcuts")
    if options.get("desktop"):
        make_shortcut(desktop_shortcut(), destination, target)
    else:
        try:
            desktop_shortcut().unlink()
        except OSError:
            pass
    if options.get("start_menu"):
        make_shortcut(startmenu_shortcut(), destination, target)
    else:
        try:
            startmenu_shortcut().unlink()
        except OSError:
            pass

    progress(78, "setup.msg_uninstaller")
    uninstaller = install_uninstaller(target, destination)

    progress(90, "setup.msg_register")
    register_uninstall(target, destination, uninstaller)

    progress(100, "setup.msg_done")


def launch(target: Path) -> None:
    subprocess.Popen([str(target / APP_EXE)], cwd=str(target), close_fds=True)
