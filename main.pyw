"""AFK Game Downloader Pro - entry point (runs silently under pythonw)."""

from __future__ import annotations

import ctypes
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

MUTEX_NAME = "Global\\AFKGameDownloaderPro_SingleInstance"


def _already_running() -> bool:
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if handle:
        globals()["_mutex_handle"] = handle  # keep the handle alive for the process lifetime
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def _message(text: str, flags: int) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, text, "AFK Game Downloader Pro", flags)
    except Exception:  # noqa: BLE001
        pass


def _fatal(exc: BaseException) -> None:
    from afkdl.config import LOG_PATH
    from afkdl.i18n import tr

    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write("\n=== CRASH ===\n")
            handle.write("".join(traceback.format_exception(exc)))
    except OSError:
        pass
    _message(tr("shell.crash", error=exc, path=LOG_PATH), 0x10)


def main() -> int:
    from afkdl import i18n
    from afkdl.config import Config

    cfg = Config()
    i18n.set_lang(str(cfg.get("language") or "en"))

    if _already_running():
        _message(i18n.tr("shell.already_running"), 0x40)
        return 0

    try:
        from afkdl.ui import main as ui_main

        ui_main()
    except BaseException as exc:  # noqa: BLE001
        _fatal(exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
