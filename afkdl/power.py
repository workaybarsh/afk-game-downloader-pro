"""Power actions: shutdown, restart, sleep, hibernate."""

from __future__ import annotations

import ctypes
import subprocess


def _spawn(args: list[str]) -> None:
    subprocess.Popen(args, close_fds=True)


def shutdown(message: str = "AFK Game Downloader Pro: downloads finished.") -> None:
    _spawn(["shutdown", "/s", "/t", "0", "/c", message])


def restart(message: str = "AFK Game Downloader Pro: downloads finished.") -> None:
    _spawn(["shutdown", "/r", "/t", "0", "/c", message])


def cancel_pending() -> None:
    try:
        _spawn(["shutdown", "/a"])
    except OSError:
        pass


def sleep_pc() -> None:
    # SetSuspendState(bHibernate=False, bForce=True, bWakeupEventsDisabled=False)
    ctypes.windll.powrprof.SetSuspendState(0, 1, 0)


def hibernate_pc() -> None:
    ctypes.windll.powrprof.SetSuspendState(1, 1, 0)


def lock_pc() -> None:
    ctypes.windll.user32.LockWorkStation()


def execute(action: str) -> None:
    action = (action or "shutdown").lower()
    if action == "shutdown":
        shutdown()
    elif action == "restart":
        restart()
    elif action == "sleep":
        sleep_pc()
    elif action == "hibernate":
        hibernate_pc()
    elif action == "lock":
        lock_pc()
    else:
        raise ValueError(f"Unknown action: {action}")
