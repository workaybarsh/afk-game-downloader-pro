"""Settings persisted to %APPDATA%\\AFKGameDownloaderPro\\config.json."""

from __future__ import annotations

import json
import os
import pathlib

BASE_DIR = pathlib.Path(os.environ.get("APPDATA") or pathlib.Path.home()) / "AFKGameDownloaderPro"
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "afkdl.log"

# Order used by the action combobox; labels come from i18n ("action.<key>").
ACTION_ORDER = ["shutdown", "restart", "sleep", "hibernate", "test"]

DEFAULTS: dict = {
    "language": "en",
    "action": "shutdown",          # what to do when everything is done
    "delay_seconds": 60,           # countdown before the action
    "confirm_seconds": 120,        # calm window required before declaring "done"
    "watch_steam": True,
    "watch_epic": True,
    "poll_seconds": 2.0,
    "auto_refresh_seconds": 60,     # periodic library re-scan (0 = off)
    "show_log": False,              # event log: closed on first run, then remembered
    "min_rate_mbps": 1.0,          # above this the download is considered alive
    "stop_steam_on_action": False,
    "window_geometry": "",
}


class Config(dict):
    def __init__(self) -> None:
        super().__init__(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(CONFIG_PATH.read_text("utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(raw, dict):
            for key, value in raw.items():
                if key in DEFAULTS:
                    self[key] = value

    def save(self) -> None:
        try:
            BASE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = CONFIG_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(dict(self), indent=2, ensure_ascii=False), "utf-8")
            tmp.replace(CONFIG_PATH)
        except OSError:
            pass

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    def __setattr__(self, key, value):
        self[key] = value
