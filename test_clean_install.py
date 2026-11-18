"""End-to-end clean-install test with the real Setup.exe.

Install silently -> verify -> launch the app -> close it with WM_CLOSE (the X)
-> verify the process is really gone -> uninstall with the installed uninstaller
-> verify nothing is left behind.

Run:  python test_clean_install.py
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
import winreg
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from setup_tool import ops  # noqa: E402

CHECKS = 0
SETUP = HERE / "dist" / "AFK Game Downloader Pro Setup.exe"
TARGET = Path(os.environ["LOCALAPPDATA"]) / "Programs" / ops.APP_NAME
SETTINGS = Path(os.environ["APPDATA"]) / "AFKGameDownloaderPro"


def check(name: str, condition: bool, extra: str = "") -> None:
    global CHECKS
    if condition:
        CHECKS += 1
        print(f"  [OK]   {name}")
    else:
        print(f"  [FAIL] {name} {extra}")
        raise SystemExit(1)


def reg_key_exists(subkey: str) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey):
            return True
    except OSError:
        return False


def reg_value_exists(subkey: str, name: str) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
            winreg.QueryValueEx(key, name)
            return True
    except OSError:
        return False


def main() -> int:
    print("\n Preconditions")
    check("setup exe exists", SETUP.is_file(), str(SETUP))
    # start from a clean slate
    subprocess.run(
        ["cmd", "/c", "taskkill", "/IM", ops.APP_EXE, "/F"],
        capture_output=True,
        creationflags=0x08000000,
    )
    for path in (TARGET,):
        if path.exists():
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Remove-Item -LiteralPath '{path}' -Recurse -Force"],
                capture_output=True,
                creationflags=0x08000000,
            )
    print("     starting from a clean machine")

    print("\n Silent install (the same code path the wizard uses)")
    result_file = Path(os.environ["TEMP"]) / "afkdl_setup_result.txt"
    result_file.unlink(missing_ok=True)
    proc = subprocess.run([str(SETUP), "--silent"], capture_output=True, timeout=300)
    time.sleep(1)
    check("installer exit code 0", proc.returncode == 0, str(proc.returncode))
    check("result file says OK", result_file.is_file() and result_file.read_text("utf-8").startswith("OK"))
    check("app installed", (TARGET / ops.APP_EXE).is_file())
    check("uninstaller installed", (TARGET / ops.UNINSTALLER_EXE).is_file())
    check("desktop shortcut", ops.desktop_shortcut().is_file())
    check("start menu shortcut", ops.startmenu_shortcut().is_file())
    check("Apps & Features entry", reg_key_exists(ops.UNINSTALL_SUBKEY))

    icon = subprocess.run(
        [sys.executable, "tools/check_icon.py", str(TARGET / ops.APP_EXE), str(TARGET / ops.UNINSTALLER_EXE)],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    check("installed binaries carry the icon", icon.returncode == 0, icon.stdout)

    print("\n Launch and close with the X button")
    subprocess.Popen([str(TARGET / ops.APP_EXE)], cwd=str(TARGET))
    time.sleep(8)
    check("app is running", ops.app_running())

    from afkdl.procs import list_processes

    pids = [pid for pid, name in list_processes() if name.lower() == ops.APP_EXE.lower()]
    # one-file builds run a bootloader process plus the real app process
    check("app process(es) present", 1 <= len(pids) <= 2, str(pids))
    hwnd = 0
    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = wintypes.HWND
    for _ in range(20):
        hwnd = user32.FindWindowW(None, "AFK Game Downloader Pro v1.0.0")
        if hwnd:
            break
        time.sleep(1)
    check("window found", bool(hwnd))
    user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE (the X button)
    time.sleep(6)
    check("app exited after closing", not ops.app_running())
    leftover = [name for _, name in list_processes() if name.lower() in (ops.APP_EXE.lower(), "pythonw.exe")]
    check("no background process left", not leftover, str(leftover))

    print("\n Uninstall with the installed wizard (quiet)")
    env = dict(os.environ)
    uninstaller = TARGET / ops.UNINSTALLER_EXE
    proc = subprocess.run(
        [str(uninstaller), "--quiet", "--target", str(TARGET)],
        env=env,
        capture_output=True,
        timeout=180,
    )
    time.sleep(8)
    check("uninstaller exit code 0", proc.returncode == 0, str(proc.returncode))
    check("install folder removed", not TARGET.exists(), str(TARGET))
    check("desktop shortcut removed", not ops.desktop_shortcut().exists())
    check("start menu shortcut removed", not ops.startmenu_shortcut().exists())
    check("Apps & Features entry removed", not reg_key_exists(ops.UNINSTALL_SUBKEY))
    check("autostart entry removed", not reg_value_exists(ops.RUN_KEY, ops.RUN_VALUE))
    check("settings removed", not SETTINGS.exists(), str(SETTINGS))

    print(f"\n CLEAN INSTALL TEST PASSED ({CHECKS} checks)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
