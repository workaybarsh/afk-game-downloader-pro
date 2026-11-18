"""Epic-specific tests: the same scenarios as Steam, plus Epic's own parsing rules.

Run:  python test_epic.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time as real_time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import afkdl.epic as epic_mod  # noqa: E402
from afkdl.config import Config  # noqa: E402
from afkdl.detector import Detector  # noqa: E402
from afkdl.epic import EpicApp, EpicSource, app_key, egstore_finished  # noqa: E402

CHECKS = 0


def check(name: str, condition: bool, extra: str = "") -> None:
    global CHECKS
    if condition:
        CHECKS += 1
        print(f"  [OK]   {name}")
    else:
        print(f"  [FAIL] {name} {extra}")
        raise SystemExit(1)


class Clock:
    def __init__(self) -> None:
        self.now = 2_000_000.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSteam:
    available = False
    root = None
    log_path = None
    io: dict = {}
    last_rate_mbps = 0.0
    last_rate_time = 0.0

    def scan(self):
        return []

    def libraries(self):
        return []

    def invalidate_libraries(self) -> None:
        pass

    def fresh_rate(self, within: float = 150.0) -> float:
        return 0.0

    def rate_is_live(self, *a, **k) -> bool:
        return False

    def io_write_bps(self) -> float:
        return 0.0

    def logged_state(self, appid: str):
        return ()


class FakeEpic:
    available = True
    io: dict = {}

    def __init__(self) -> None:
        self.apps: list[EpicApp] = []
        self.rate = False

    def scan(self):
        return [copy.deepcopy(a) for a in self.apps]

    def io_write_bps(self) -> float:
        return 0.0

    def rate_is_live(self, *a, **k) -> bool:
        return self.rate


def make_config() -> Config:
    cfg = Config()
    cfg.update(
        {
            "watch_steam": False,
            "watch_epic": True,
            "confirm_seconds": 120,
            "delay_seconds": 60,
            "action": "test",
            "poll_seconds": 1.0,
            "min_rate_mbps": 1.0,
        }
    )
    return cfg


def app(name: str, *, active: bool, complete: bool, size: int = 0) -> EpicApp:
    location = f"C:/Games/{name}"
    return EpicApp(
        key=app_key(location),
        app_name=name.lower(),
        name=name,
        install_location=location,
        incomplete=not complete,
        install_size=size,
        active=active,
        complete=complete,
        source="queue" if not complete else "manifest",
    )


def new_detector(cfg: Config) -> Detector:
    det = Detector(cfg)
    det.steam = FakeSteam()
    det.epic = FakeEpic()
    return det


def main() -> int:
    clock = Clock()
    real_time.time = lambda: clock.now  # type: ignore[assignment]
    epic_time = epic_mod.time
    epic_time.time = lambda: clock.now  # type: ignore[assignment]

    try:
        cfg = make_config()

        print("\n Epic 1: download -> finish -> action")
        det = new_detector(cfg)
        det.epic.apps = [app("Control", active=True, complete=False)]
        status = det.step()
        check("epic download detected", status.phase == "downloading", status.phase)
        check("epic app in the list", any(a["source"] == "Epic" for a in status.apps))
        check("epic app is watched", status.watching_count == 1, str(status.watching_count))

        clock.advance(60)
        det.epic.apps = [app("Control", active=True, complete=False)]
        status = det.step()
        check("no action while downloading", status.phase == "downloading")

        clock.advance(10)
        det.epic.apps = [app("Control", active=False, complete=True, size=12_000_000_000)]
        status = det.step()
        check("finish -> verification", status.phase == "draining", status.phase)

        clock.advance(130)
        status = det.step()
        check("ready after the window", status.phase == "ready", status.phase)
        check("countdown started", status.countdown_left is not None)

        clock.advance(61)
        status = det.step()
        check("action taken in test mode", status.phase == "done", status.phase)

        print("\n Epic 2: download keeps running during verification")
        clock.advance(10)
        det = new_detector(cfg)
        det.epic.apps = [app("Control", active=True, complete=False)]
        det.step()
        clock.advance(10)
        det.epic.apps = [app("Control", active=False, complete=True)]
        status = det.step()
        check("verification started", status.phase == "draining", status.phase)
        clock.advance(30)
        det.epic.apps = [app("Control", active=True, complete=False)]
        status = det.step()
        check("download back -> downloading", status.phase == "downloading", status.phase)

        print("\n Epic 3: two epic downloads at once")
        clock.advance(10)
        det = new_detector(cfg)
        det.epic.apps = [
            app("Control", active=True, complete=False),
            app("DOOM 64", active=True, complete=False),
        ]
        status = det.step()
        check("both tracked", len(det.tracked) == 2, str(list(det.tracked)))
        clock.advance(30)
        det.epic.apps = [
            app("Control", active=False, complete=True),
            app("DOOM 64", active=True, complete=False),
        ]
        status = det.step()
        check("one finished, one running", status.phase == "downloading", status.phase)
        clock.advance(30)
        det.epic.apps = [
            app("Control", active=False, complete=True),
            app("DOOM 64", active=False, complete=True),
        ]
        status = det.step()
        check("both finished -> verification", status.phase == "draining", status.phase)
        clock.advance(130)
        status = det.step()
        check("ready with both", status.phase == "ready", status.phase)
        check("two in the proof", len(status.tracked) == 2)

        print("\n Epic 4: un-ticking the only epic download")
        clock.advance(10)
        det = new_detector(cfg)
        det.epic.apps = [app("Control", active=True, complete=False)]
        det.step()
        det.set_watched(app_key("C:/Games/Control"), False)
        clock.advance(10)
        det.epic.apps = [app("Control", active=False, complete=True)]
        status = det.step()
        check("un-watched -> waiting", status.phase == "waiting", status.phase)

        print("\n Epic 5: Stop / Cancel")
        clock.advance(10)
        det = new_detector(cfg)
        det.epic.apps = [app("Control", active=True, complete=False)]
        det.step()
        det.set_enabled(False)
        det.epic.apps = [app("Control", active=False, complete=True)]
        status = det.step()
        check("stopped", status.phase == "stopped", status.phase)
        check("no apps listed when stopped", len(status.apps) == 0, str(len(status.apps)))

        print("\n Epic 6: install folder disappears (cancelled install)")
        clock.advance(10)
        det = new_detector(cfg)
        det.epic.apps = [app("Control", active=True, complete=False)]
        det.step()
        clock.advance(10)
        det.epic.apps = []
        det.step()
        for _ in range(10):
            clock.advance(60)
            status = det.step()
        check("missing epic app -> interrupted", status.phase == "interrupted", status.phase)

        print("\n Epic 7: .egstore completion marker")
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "SomeGame"
            egstore = game / ".egstore"
            (egstore / "bps").mkdir(parents=True)
            (egstore / "Pending").mkdir()
            (egstore / ".lock").write_text("")
            (egstore / "bps" / "chunk.manifest").write_text("x" * 900)  # must NOT count
            check("in-progress install is not finished", not egstore_finished(str(game)))
            (egstore / "ABCDEF0123456789.manifest").write_text("x" * 900)
            check("manifest marker means finished", egstore_finished(str(game)))

        print("\n Epic 8: DownloadState queue parsing")
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            payload = [
                {
                    "AppId": {"AppName": "hash-control"},
                    "InstallConfig": {"DestinationPath": "C:/Games/Control"},
                    "InstallType": "Install",
                },
                {
                    "AppId": {"AppName": "hash-old"},
                    "InstallConfig": {"DestinationPath": "C:/Games/Old"},
                    "InstallType": "Uninstall",
                },
                {
                    "AppId": {"AppName": "hash-dlc"},
                    "InstallConfig": {"DestinationPath": "C:/Games/DLC"},
                    "InstallType": "Update",
                },
                {
                    "AppId": {"AppName": "hash-empty"},
                    "InstallConfig": {"DestinationPath": ""},
                    "InstallType": "Install",
                },
            ]
            (state_dir / "DownloadState_test.json").write_text(json.dumps(payload), "utf-8")
            original = epic_mod.DOWNLOAD_STATE_DIRS
            epic_mod.DOWNLOAD_STATE_DIRS = [state_dir]
            try:
                tasks = EpicSource()._queue_tasks()
            finally:
                epic_mod.DOWNLOAD_STATE_DIRS = original
            destinations = sorted(t["destination"] for t in tasks)
            check("install + update parsed", destinations == ["C:/Games/Control", "C:/Games/DLC"], str(destinations))
            check("uninstall ignored", all(t["install_type"] != "uninstall" for t in tasks))
            check("empty destination ignored", len(tasks) == 2, str(len(tasks)))

        print("\n Epic 9: key is stable across queue and manifest")
        check(
            "same key for both separators",
            app_key("C:/Program Files/Epic Games/Control") == app_key(r"C:\Program Files\Epic Games\Control"),
            app_key("C:/Program Files/Epic Games/Control"),
        )

        print(f"\n ALL EPIC TESTS PASSED ({CHECKS} checks)\n")
        return 0
    finally:
        real_time.time = real_time.time  # noqa: PLW0127
        epic_time.time = real_time.time  # type: ignore[assignment]


if __name__ == "__main__":
    sys.exit(main())
