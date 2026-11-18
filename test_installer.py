"""End-to-end installer test: install to a temp folder, verify, uninstall.

Run:  python test_installer.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import winreg
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from setup_tool import ops  # noqa: E402

CHECKS = 0


def check(name: str, condition: bool, extra: str = "") -> None:
    global CHECKS
    if condition:
        CHECKS += 1
        print(f"  [OK]   {name}")
    else:
        print(f"  [FAIL] {name} {extra}")
        raise SystemExit(1)


def reg_value_exists(root, subkey: str, name: str) -> bool:
    try:
        with winreg.OpenKey(root, subkey) as key:
            winreg.QueryValueEx(key, name)
            return True
    except OSError:
        return False


def reg_exists(root, subkey: str) -> bool:
    try:
        with winreg.OpenKey(root, subkey):
            return True
    except OSError:
        return False



def same_file(candidate: str, expected: Path) -> bool:
    try:
        return os.path.samefile(candidate, expected)
    except OSError:
        return os.path.normcase(os.path.abspath(candidate)) == os.path.normcase(str(expected))


def shortcut_info(link: Path) -> tuple[str, str]:
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('"
        + str(link)
        + "'); Write-Output ($s.TargetPath + '|' + $s.IconLocation)"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=0x08000000,
        timeout=60,
    )
    text = (proc.stdout or "").strip()
    target, _, icon = text.partition("|")
    return target, icon


def main() -> int:
    target = Path(os.environ["TEMP"]) / "afkdl_install_test"
    fake_appdata = Path(os.environ["TEMP"]) / "afkdl_appdata_test"
    fake_appdata.mkdir(parents=True, exist_ok=True)

    print("\n Payload")
    payload = ops.payload_exe()
    check("bundled app exe found", payload.is_file(), str(payload))
    print(f"     {payload}  ({payload.stat().st_size / 1e6:.1f} MB)")

    print("\n Install")
    steps: list[tuple[int, str]] = []
    ops.install(
        target,
        {"desktop": True, "start_menu": True, "autostart": True},
        lambda percent, key: steps.append((percent, key)),
    )
    check("progress reported", len(steps) >= 5 and steps[-1][0] == 100, str(steps[-3:]))
    check("app exe installed", (target / ops.APP_EXE).is_file())
    gui_uninstaller = target / ops.UNINSTALLER_EXE
    check(
        "uninstaller written",
        gui_uninstaller.is_file() or (target / "Uninstall.cmd").is_file(),
    )
    check("desktop shortcut", ops.desktop_shortcut().is_file(), str(ops.desktop_shortcut()))
    check("start menu shortcut", ops.startmenu_shortcut().is_file(), str(ops.startmenu_shortcut()))
    check("uninstall registry entry", reg_exists(winreg.HKEY_CURRENT_USER, ops.UNINSTALL_SUBKEY))
    print(f"     installed to {target}")


    print("\n Icons and shortcuts")
    icon_test = subprocess.run(
        [sys.executable, "tools/check_icon.py", str(target / ops.APP_EXE)],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    check("installed exe carries the app icon", icon_test.returncode == 0, icon_test.stdout.strip())
    print(f"     {icon_test.stdout.strip()}")

    desktop_target, desktop_icon = shortcut_info(ops.desktop_shortcut())
    check("desktop shortcut points to the app", same_file(desktop_target, target / ops.APP_EXE), desktop_target)
    check(
        "desktop shortcut uses the app icon",
        same_file(desktop_icon.split(",")[0], target / ops.APP_EXE),
        desktop_icon,
    )

    menu_target, menu_icon = shortcut_info(ops.startmenu_shortcut())
    check("start menu shortcut points to the app", same_file(menu_target, target / ops.APP_EXE), menu_target)

    print("\n Launch the installed app")
    subprocess.Popen([str(target / ops.APP_EXE)], cwd=str(target))
    time.sleep(6)
    check("installed app is running", ops.app_running())
    ops.close_app()
    time.sleep(1)
    check("installed app closed again", not ops.app_running())

    print("\n Uninstall (quiet)")
    env = dict(os.environ)
    env["APPDATA"] = str(fake_appdata)
    if gui_uninstaller.is_file():
        subprocess.run(
            [str(gui_uninstaller), "--quiet", "--target", str(target)],
            env=env,
            capture_output=True,
            creationflags=0x08000000,
            timeout=120,
        )
    else:
        subprocess.run(
            ["cmd", "/c", str(target / "Uninstall.cmd"), "/quiet"],
            env=env,
            capture_output=True,
            creationflags=0x08000000,
            timeout=90,
        )
    time.sleep(6)  # the script removes the folder from a detached helper
    check("folder removed", not target.exists(), str(target))
    check("desktop shortcut removed", not ops.desktop_shortcut().exists())
    check("start menu shortcut removed", not ops.startmenu_shortcut().exists())
    check("uninstall registry entry removed", not reg_exists(winreg.HKEY_CURRENT_USER, ops.UNINSTALL_SUBKEY))
    check(
        "autostart registry entry removed",
        not reg_value_exists(winreg.HKEY_CURRENT_USER, ops.RUN_KEY, ops.RUN_VALUE),
    )

    print(f"\n ALL INSTALLER TESTS PASSED ({CHECKS} checks)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
