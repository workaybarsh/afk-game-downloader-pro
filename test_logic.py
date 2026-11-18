"""Decision-engine tests with synthetic scenarios (no network, no real files).

Run:  python test_logic.py
"""

from __future__ import annotations

import copy
import sys
import time as real_time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from afkdl import detector as detector_mod  # noqa: E402
from afkdl.config import Config  # noqa: E402
from afkdl.detector import Detector  # noqa: E402
from afkdl.steam import SteamApp, SteamSource  # noqa: E402

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
        self.now = 1_000_000.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeSteam:
    available = True
    root = Path("X:/FakeSteam")
    log_path = Path("X:/FakeSteam/logs/content_log.txt")
    last_rate_mbps = 0.0
    last_rate_time = 0.0
    io: dict = {}

    def __init__(self) -> None:
        self.template: SteamApp | None = None
        self.multi: list[SteamApp] = []
        self.rate = 0.0
        self.state_words: tuple[str, ...] = ()

    def logged_state(self, appid: str) -> tuple[str, ...]:
        return self.state_words

    def libraries(self):
        return [self.root]

    def invalidate_libraries(self) -> None:
        pass

    def scan(self):
        if self.multi:
            return [copy.deepcopy(app) for app in self.multi]
        return [copy.deepcopy(self.template)] if self.template else []

    def fresh_rate(self, within: float = 150.0) -> float:
        return self.rate

    def rate_is_live(self, min_mbps: float = 1.0, within: float = 150.0) -> bool:
        return self.rate >= min_mbps

    def io_write_bps(self) -> float:
        return 0.0


class FakeEpic:
    available = True
    io: dict = {}

    def scan(self):
        return []

    def io_write_bps(self) -> float:
        return 0.0

    def rate_is_live(self, *a, **k) -> bool:
        return False


def make_config() -> Config:
    cfg = Config()
    cfg.update(
        {
            "watch_steam": True,
            "watch_epic": False,
            "confirm_seconds": 120,
            "delay_seconds": 60,
            "poll_seconds": 1.0,
            "min_rate_mbps": 1.0,
            "action": "test",
        }
    )
    return cfg


def busy_app(downloaded: int = 100, total: int = 1000) -> SteamApp:
    return SteamApp(
        appid="730",
        name="Test Game",
        library="X",
        flags=0x406,  # Fully Installed + Update Required + Update Started
        downloaded=downloaded,
        total=total,
        state_words=("Update Running", "Downloading", "Staging"),
        active=True,
        complete=False,
    )


def done_app(total: int = 1000) -> SteamApp:
    return SteamApp(
        appid="730",
        name="Test Game",
        library="X",
        flags=0x4,  # Fully Installed
        downloaded=total,
        total=total,
        state_words=("Fully Installed",),
        active=False,
        complete=True,
    )


def new_detector(cfg: Config) -> Detector:
    det = Detector(cfg)
    det.steam = FakeSteam()
    det.epic = FakeEpic()
    return det


def main() -> int:
    clock = Clock()
    real_time.time = lambda: clock.now  # type: ignore[assignment]
    detector_mod.time.time = lambda: clock.now  # type: ignore[assignment]

    try:
        cfg = make_config()

        print("\n Scenario 1: normal download -> finish -> action")
        det = new_detector(cfg)
        det.steam.template = busy_app()
        det.steam.rate = 100.0

        status = det.step()
        check("download detected", status.phase == "downloading", status.phase)

        clock.advance(30)
        det.steam.template = busy_app(downloaded=500)
        status = det.step()
        check("no action while downloading", status.phase == "downloading")

        clock.advance(10)
        det.steam.rate = 0.0
        det.steam.template = done_app()
        status = det.step()
        check("finish -> verification window", status.phase == "draining", status.phase)
        check("does not act immediately", status.countdown_left is None)

        clock.advance(60)
        status = det.step()
        check("still verifying at 60s", status.phase == "draining")

        clock.advance(59)
        status = det.step()
        check("still verifying at 119s", status.phase == "draining")

        clock.advance(5)
        status = det.step()
        check("ready after the window", status.phase == "ready", status.phase)
        check("countdown started", status.countdown_left is not None and status.countdown_left > 0)

        clock.advance(30)
        status = det.step()
        check("countdown running, no action yet", status.phase == "ready")

        clock.advance(35)
        status = det.step()
        check("action taken in test mode", status.phase == "done", status.phase)
        check("test mode did not act on the machine", not det.enabled)

        print("\n Scenario 2: download resumes during verification")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=900)
        det.steam.rate = 100.0
        det.step()

        clock.advance(20)
        det.steam.rate = 0.0
        det.steam.template = done_app()
        status = det.step()
        check("verification started", status.phase == "draining")

        clock.advance(30)
        det.steam.rate = 90.0
        det.steam.template = busy_app(downloaded=950)
        status = det.step()
        check("new download -> back to downloading", status.phase == "downloading", status.phase)

        clock.advance(30)
        det.steam.rate = 0.0
        det.steam.template = done_app()
        status = det.step()
        check("verification restarted", status.phase == "draining")

        print("\n Scenario 3: bytes missing -> never act")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()

        clock.advance(10)
        det.steam.rate = 0.0
        partial = done_app(total=1000)
        partial.downloaded = 700  # flags say installed, bytes say otherwise
        det.steam.template = partial
        status = det.step()
        check("verification started (3)", status.phase == "draining")

        for _ in range(10):
            clock.advance(60)
            status = det.step()
        check("bytes missing blocks the action", status.phase == "draining", status.phase)

        print("\n Scenario 4: live transfer rate blocks the action")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()

        clock.advance(10)
        det.steam.rate = 5.0  # transfer alive, manifest not updated yet
        det.steam.template = done_app()
        det.step()
        for _ in range(6):
            clock.advance(30)
            status = det.step()
        check("live rate blocks the action", status.phase != "ready", status.phase)

        print("\n Scenario 5: nothing downloaded -> never act")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = done_app()
        det.steam.rate = 0.0
        for _ in range(20):
            clock.advance(60)
            status = det.step()
        check("no download seen -> no action", status.phase == "waiting", status.phase)

        print("\n Scenario 6: cancel")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()
        clock.advance(10)
        det.steam.rate = 0.0
        det.steam.template = done_app()
        det.step()
        clock.advance(130)
        status = det.step()
        check("ready", status.phase == "ready", status.phase)
        det.cancel_shutdown()
        clock.advance(70)
        status = det.step()
        check("cancelled -> no action", status.phase == "stopped", status.phase)

        print("\n Scenario 7: Steam closed / manifest gone")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()
        clock.advance(10)
        det.steam.rate = 0.0
        det.steam.template = None
        det.step()
        for _ in range(6):
            clock.advance(60)
            status = det.step()
        check("missing manifest blocks the action", status.phase != "ready", status.phase)


        print("\n Scenario 8: manifest says done but Steam log still shows work")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()

        clock.advance(10)
        det.steam.rate = 0.0
        det.steam.template = done_app()
        det.steam.state_words = ("Update Running", "Downloading")
        det.step()
        for _ in range(8):
            clock.advance(60)
            status = det.step()
        check("log state blocks the action", status.phase != "ready", status.phase)

        print("\n Scenario 9: final re-check right before acting")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()
        clock.advance(10)
        det.steam.rate = 0.0
        det.steam.template = done_app()
        det.step()
        clock.advance(130)
        status = det.step()
        check("ready after verification", status.phase == "ready", status.phase)

        # the download silently resumes between verification and the countdown end
        det.steam.state_words = ("Update Running", "Downloading")
        clock.advance(61)
        status = det.step()
        check("re-check cancels the action", status.phase != "done", status.phase)
        check("went back to verifying", status.phase in ("draining", "downloading"), status.phase)


        print("\n Scenario 10: Stop button")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()
        det.set_enabled(False)
        det.steam.rate = 0.0
        det.steam.template = done_app()
        status = det.step()
        check("stopped after Stop", status.phase == "stopped", status.phase)
        check("no game list flood when stopped", len(status.apps) == 0, str(len(status.apps)))
        clock.advance(600)
        status = det.step()
        check("stays stopped", status.phase == "stopped", status.phase)

        print("\n Scenario 11: un-ticking the only watched download")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        status = det.step()
        check("armed while downloading", status.phase == "downloading")
        det.set_watched("steam:730", False)
        clock.advance(10)
        det.steam.rate = 0.0
        det.steam.template = done_app()
        status = det.step()
        check("un-watched -> waiting, not verifying", status.phase == "waiting", status.phase)
        clock.advance(600)
        status = det.step()
        check("still no action", status.phase != "ready", status.phase)

        print("\n Scenario 12: un-ticked download keeps running")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()
        det.set_watched("steam:730", False)
        det.steam.template = busy_app(downloaded=400)
        status = det.step()
        check("ignored download does not re-arm", not det.armed, status.phase)
        check("phase stays waiting", status.phase == "waiting", status.phase)

        print("\n Scenario 13: Steam closed for good -> interrupted")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.template = busy_app(downloaded=100)
        det.steam.rate = 50.0
        det.step()
        clock.advance(10)
        det.steam.rate = 0.0
        det.steam.template = None
        det.step()
        for _ in range(10):
            clock.advance(60)
            status = det.step()
        check("missing manifests -> interrupted", status.phase == "interrupted", status.phase)
        check("interrupted does not act", not det.enabled)

        print("\n Scenario 14: Steam state parsing rules")
        src = SteamSource.__new__(SteamSource)

        def make(flags, words, delayed=False, downloaded=500, total=1000):
            app = SteamApp(
                appid="1",
                name="t",
                library="x",
                flags=flags,
                downloaded=downloaded,
                total=total,
                state_words=words,
                delayed=delayed,
            )
            app.active = src._is_active(app)
            app.complete = src._is_complete(app)
            return app

        check("paused download is still active", make(0x402, ("Update Paused",)).active)
        check("delayed update is not a download", not make(0x406, ("Fully Installed", "Update Required"), delayed=True).active)
        check("queued download is active", make(0x406, ("Update Required", "Update Queued")).active)
        check("fully installed is complete", make(0x4, ("Fully Installed",), downloaded=1000).complete)
        check("update-started bit is not complete", not make(0x404, ("Fully Installed",)).complete)
        check("update-required bit is not complete", not make(0x6, ("Fully Installed",)).complete)


        print("\n Scenario 15: two downloads at once")
        clock.advance(10)
        det = new_detector(cfg)

        def game(appid: str, name: str, downloaded: int, total: int, active: bool):
            return SteamApp(
                appid=appid,
                name=name,
                library="X",
                flags=0x406 if active else 0x4,
                downloaded=downloaded,
                total=total,
                state_words=("Update Running", "Downloading") if active else ("Fully Installed",),
                active=active,
                complete=not active,
            )

        det.steam.multi = [game("111", "Game A", 100, 1000, True), game("222", "Game B", 200, 2000, True)]
        det.steam.rate = 80.0
        status = det.step()
        check("both downloads tracked", len(det.tracked) == 2, str(list(det.tracked)))
        check("phase downloading", status.phase == "downloading")
        check("two watched", status.watching_count == 2, str(status.watching_count))

        # Game A finishes, Game B keeps going
        clock.advance(60)
        det.steam.multi = [game("111", "Game A", 1000, 1000, False), game("222", "Game B", 900, 2000, True)]
        status = det.step()
        check("still downloading while B runs", status.phase == "downloading", status.phase)
        check("no countdown started", status.countdown_left is None)
        for _ in range(6):
            clock.advance(60)
            status = det.step()
        check("never verifies while B runs", status.phase == "downloading", status.phase)

        # Game B finishes too
        clock.advance(60)
        det.steam.rate = 0.0
        det.steam.multi = [game("111", "Game A", 1000, 1000, False), game("222", "Game B", 2000, 2000, False)]
        status = det.step()
        check("verification starts when both are done", status.phase == "draining", status.phase)
        clock.advance(130)
        status = det.step()
        check("ready when both are done", status.phase == "ready", status.phase)
        check("both in the proof", len(status.tracked) == 2, str(len(status.tracked)))

        print("\n Scenario 16: third download starts during the countdown")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.multi = [game("111", "Game A", 100, 1000, True), game("222", "Game B", 200, 2000, True)]
        det.steam.rate = 50.0
        det.step()
        clock.advance(10)
        det.steam.rate = 0.0
        det.steam.multi = [game("111", "Game A", 1000, 1000, False), game("222", "Game B", 2000, 2000, False)]
        det.step()
        clock.advance(130)
        status = det.step()
        check("ready before the third download", status.phase == "ready", status.phase)
        det.steam.rate = 70.0
        det.steam.multi = [
            game("111", "Game A", 1000, 1000, False),
            game("222", "Game B", 2000, 2000, False),
            game("333", "Game C", 50, 5000, True),
        ]
        clock.advance(30)
        status = det.step()
        check("third download cancels the countdown", status.phase == "downloading", status.phase)
        check("third download tracked", "steam:333" in det.tracked)

        print("\n Scenario 17: one of two is un-ticked")
        clock.advance(10)
        det = new_detector(cfg)
        det.steam.multi = [game("111", "Game A", 100, 1000, True), game("222", "Game B", 200, 2000, True)]
        det.steam.rate = 80.0
        det.step()
        det.set_watched("steam:111", False)
        # A finishes, B still runs
        clock.advance(30)
        det.steam.multi = [game("111", "Game A", 1000, 1000, False), game("222", "Game B", 900, 2000, True)]
        status = det.step()
        check("only B gates now", list(det.tracked) == ["steam:222"], str(list(det.tracked)))
        clock.advance(30)
        det.steam.rate = 0.0
        det.steam.multi = [game("111", "Game A", 1000, 1000, False), game("222", "Game B", 2000, 2000, False)]
        status = det.step()
        check("draining once B is done", status.phase == "draining", status.phase)
        clock.advance(130)
        status = det.step()
        check("ready with only B", status.phase == "ready", status.phase)

        print(f"\n ALL TESTS PASSED ({CHECKS} checks)\n")
        return 0
    finally:
        real_time.time = real_time.time  # noqa: PLW0127
        detector_mod.time.time = real_time.time  # type: ignore[assignment]


if __name__ == "__main__":
    sys.exit(main())
