"""Console diagnostics: what does the program see, and what decision would it make?

Usage:
    python diagnose.py            # single report
    python diagnose.py --loop     # live view, refreshed every 5s
    python diagnose.py --tr       # Turkish output
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from afkdl import i18n  # noqa: E402
from afkdl.config import Config  # noqa: E402
from afkdl.detector import Detector  # noqa: E402
from afkdl.i18n import tr  # noqa: E402
from afkdl.util import ago, fmt_bytes, fmt_duration, fmt_speed  # noqa: E402

BAR = "=" * 72
DASH = "-" * 72


def _utf8() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass


def report(detector: Detector, first: bool) -> None:
    if first:
        print(BAR)
        print(f" {tr('ui.title')} — DIAGNOSTICS")
        print(BAR)

    status = detector.step()

    print(DASH)
    print(f" {tr('ui.last_check', time=time.strftime('%d.%m.%Y %H:%M:%S'))}")
    print(f" Steam root      : {detector.steam.root or '—'}")
    print(f" Steam running   : {'yes' if status.steam_running else 'no'}")
    rate_age = time.time() - detector.steam.last_rate_time if detector.steam.last_rate_time else None
    print(f" Steam rate      : {detector.steam.fresh_rate():.1f} Mbps  ({ago(rate_age)})")
    print(f" Steam log       : {detector.steam.log_path}")
    for lib in detector.steam.libraries():
        print(f"   library       : {lib}")
    print(f" Epic manifests  : {'found' if detector.epic.available else 'not found'}")
    print(f" Epic running    : {'yes' if status.epic_running else 'no'}")
    print(f" Disk IO write   : {fmt_speed(status.io_bps)}")
    print(DASH)
    print(f" PHASE           : {status.phase.upper()}")
    print(f" Detail          : {status.detail}")

    print(DASH)
    if status.apps:
        print(" APPS")
        for app in status.apps:
            tag = "ACTIVE" if app["active"] else ("DONE" if app["complete"] else "idle")
            print(f"  [{app['source']}/{tag}] {app['name']}")
            if app.get("total"):
                line = f"      {fmt_bytes(app['downloaded'])} / {fmt_bytes(app['total'])}"
            else:
                line = "      size unknown"
            if app.get("progress") is not None:
                line += f"  ({app['progress'] * 100:.1f}%)"
            if app.get("rate_bps"):
                line += f"  {fmt_speed(app['rate_bps'])}"
            if app.get("eta"):
                line += f"  eta ~{fmt_duration(app['eta'])}"
            if app.get("note_key"):
                line += f"  [{tr(app['note_key'])}]"
            print(line)
    else:
        print(" APPS            : no active downloads")

    print(DASH)
    print(" DECISION")
    if status.phase == "ready":
        print(f"  >> SHUTDOWN CONFIRMED: action in {int(status.countdown_left or 0)}s")
    elif status.phase in ("downloading", "draining"):
        print("  >> NO ACTION — download running / still being verified")
    elif status.phase == "waiting":
        print("  >> NO ACTION — no download seen yet")
    elif status.phase == "stopped":
        print("  >> Monitoring is off")
    else:
        print(f"  >> {tr('phase.' + status.phase)} — {status.detail}")
    sys.stdout.flush()


def main() -> int:
    _utf8()
    if "--tr" in sys.argv:
        i18n.set_lang("tr")

    cfg = Config()
    cfg["action"] = "test"  # diagnostics never touch the machine
    detector = Detector(cfg, lambda key, params, level="info": print(f"  · {tr(key, **params)}"))

    if "--loop" not in sys.argv:
        report(detector, True)
        return 0

    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            report(detector, True)
            time.sleep(5)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
