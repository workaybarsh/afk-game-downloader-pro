"""Epic Games download detection.

Epic changed its downloader ("EOSH patcher"). Modern launcher versions do **not**
write `bIsIncompleteInstall: true` while a game downloads, so the old manifest
check alone misses every download. Evidence used now:

  1) `...\\Data\\DownloadManager\\DownloadState_*.json`
     The live task queue. Each entry has the destination path and the install type
     (Install / Update / Repair / Uninstall). This is what tells us *what* is being
     installed, including games that have no manifest yet.
  2) `<install>\\.egstore`
     An in-progress install keeps chunk files plus a `Pending`/`bps` folder; a
     finished install contains a `*.manifest` file. So: manifest present = done.
  3) `...\\Data\\Manifests\\*.item`
     The registry of installed apps (DisplayName, InstallLocation, size).
  4) Launcher log + process IO as supporting evidence.

Keys are derived from the install location, which is the only identifier that is
stable across the queue, the manifest and the `.egstore` marker.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .procs import ProcessActivity

EPIC_DATA = Path(r"C:\ProgramData\Epic\EpicGamesLauncher\Data")
MANIFEST_DIRS = [
    EPIC_DATA / "Manifests",
    Path(r"C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalledData\Manifests"),
]
DOWNLOAD_STATE_DIRS = [EPIC_DATA / "DownloadManager"]

LOG_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "EpicGamesLauncher" / "Saved" / "Logs" / "EpicGamesLauncher.log",
    Path(os.environ.get("LOCALAPPDATA", "")) / "EpicGamesLauncher" / "Saved" / "Logs" / "EpicGamesLauncher-backup.log",
]

INSTALL_TYPES = {"install", "update", "repair", "resume"}

RE_PERCENT = re.compile(r"(?i)download[^\n]*?(\d{1,3}(?:[.,]\d+)?)\s*%")
RE_INSTALL_COMPLETE = re.compile(r"(?i)(install(?:ation)?\s+complete|successfully installed|download complete)")
RE_INSTALL_START = re.compile(r"(?i)(starting (?:the )?(?:download|install)|begin(?:ning)? (?:download|install)|install(?:ation)? started)")


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(str(path).replace("/", "\\"))).strip("\\")


def app_key(install_location: str) -> str:
    return f"epic:{_norm(install_location)}"


@dataclass
class EpicApp:
    key: str
    app_name: str
    name: str
    install_location: str
    incomplete: bool
    install_size: int = 0
    manifest_path: str = ""
    manifest_time: float = 0.0
    active: bool = False
    complete: bool = False
    source: str = "manifest"


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def egstore_finished(install_location: str) -> bool:
    """True when the install folder holds a completed `.egstore` manifest.

    The completion marker always sits at the top level of `.egstore`. We must not
    recurse: the `bps`/`Pending` folders are full of chunk files and produce false
    positives (a download in progress looked "finished").
    """
    try:
        egstore = Path(install_location) / ".egstore"
        if not egstore.is_dir():
            return False
        for item in egstore.iterdir():
            if not item.is_file():
                continue
            if item.suffix.lower() in (".manifest", ".item") and item.stat().st_size > 512:
                return True
    except OSError:
        return False
    return False


class EpicSource:
    label = "Epic"

    def __init__(self) -> None:
        self.activity = ProcessActivity()
        self.io: dict[str, dict] = {}
        self.log_path = next((p for p in LOG_CANDIDATES if p.exists()), None)
        self.log_mtime: float = 0.0
        self.log_percent: dict[str, float] = {}
        self.log_last_download: float = 0.0
        self.log_state: str = ""

    @property
    def available(self) -> bool:
        return any(d.is_dir() for d in MANIFEST_DIRS) or any(d.is_dir() for d in DOWNLOAD_STATE_DIRS)

    def running(self) -> bool:
        return bool(self.activity.sample({"EpicGamesLauncher.exe"}))

    # ------------------------------------------------------------------ log
    def poll_log(self) -> None:
        if not self.log_path:
            return
        try:
            stat = self.log_path.stat()
        except OSError:
            return
        self.log_mtime = stat.st_mtime
        try:
            with self.log_path.open("rb") as handle:
                handle.seek(max(0, stat.st_size - 80_000))
                tail = handle.read().decode("utf-8", "replace")
        except OSError:
            return
        for line in tail.splitlines()[-250:]:
            if RE_INSTALL_COMPLETE.search(line):
                self.log_state = "complete"
                self.log_last_download = time.time()
                continue
            if RE_INSTALL_START.search(line):
                self.log_state = "downloading"
                self.log_last_download = time.time()
                continue
            match = RE_PERCENT.search(line)
            if match:
                try:
                    self.log_percent["current"] = float(match.group(1).replace(",", "."))
                    self.log_last_download = time.time()
                    self.log_state = "downloading"
                except ValueError:
                    pass

    # ------------------------------------------------------------------ queue
    def _queue_tasks(self) -> list[dict]:
        """Active Install/Update/Repair entries from the launcher's task queue."""
        tasks: list[dict] = []
        for directory in DOWNLOAD_STATE_DIRS:
            if not directory.is_dir():
                continue
            try:
                files = [p for p in directory.glob("DownloadState*.json") if p.is_file()]
            except OSError:
                continue
            for path in files:
                try:
                    data = json.loads(path.read_text("utf-8", "replace"))
                except (OSError, ValueError):
                    continue
                if not isinstance(data, list):
                    continue
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    install_type = str(entry.get("InstallType") or "").lower()
                    if install_type not in INSTALL_TYPES:
                        continue
                    config = entry.get("InstallConfig") or {}
                    destination = str(config.get("DestinationPath") or "").strip()
                    if not destination:
                        continue
                    app_id = entry.get("AppId") or {}
                    tasks.append(
                        {
                            "destination": destination,
                            "app_name": str(app_id.get("AppName") or ""),
                            "install_type": install_type,
                        }
                    )
        return tasks

    # ------------------------------------------------------------------ tarama
    def scan(self) -> list[EpicApp]:
        self.poll_log()
        self.io = self.activity.sample({"EpicGamesLauncher.exe"})
        apps: dict[str, EpicApp] = {}

        # 1) installed apps from the central manifests
        for directory in MANIFEST_DIRS:
            if not directory.is_dir():
                continue
            try:
                items = list(directory.glob("*.item"))
            except OSError:
                continue
            for item in items:
                try:
                    data = json.loads(item.read_text("utf-8", "replace"))
                except (OSError, ValueError):
                    continue
                if not isinstance(data, dict):
                    continue
                location = str(data.get("InstallLocation") or "").strip()
                if not location:
                    continue
                key = app_key(location)
                incomplete = bool(data.get("bIsIncompleteInstall"))
                app = EpicApp(
                    key=key,
                    app_name=str(data.get("AppName") or item.stem),
                    name=str(data.get("DisplayName") or Path(location).name),
                    install_location=location,
                    incomplete=incomplete,
                    install_size=_as_int(data.get("InstallSize")),
                    manifest_path=str(item),
                    manifest_time=_safe_mtime(item),
                    source="manifest",
                )
                app.active = incomplete
                app.complete = not incomplete and egstore_finished(location)
                apps[key] = app

        # 2) live queue: games that have no manifest yet (or are being updated)
        for task in self._queue_tasks():
            location = task["destination"]
            key = app_key(location)
            finished = egstore_finished(location)
            name = Path(location.replace("/", "\\")).name
            existing = apps.get(key)
            if finished:
                if existing:
                    existing.complete = not existing.incomplete
                    existing.active = existing.incomplete
                else:
                    apps[key] = EpicApp(
                        key=key,
                        app_name=task["app_name"] or name,
                        name=name,
                        install_location=location,
                        incomplete=False,
                        manifest_time=_safe_mtime(Path(location) / ".egstore"),
                        active=False,
                        complete=True,
                        source="queue",
                    )
                continue
            if existing and existing.complete:
                continue  # stale queue entry for an already installed game
            apps[key] = EpicApp(
                key=key,
                app_name=task["app_name"] or name,
                name=name,
                install_location=location,
                incomplete=True,
                install_size=existing.install_size if existing else 0,
                manifest_time=_safe_mtime(Path(location) / ".egstore"),
                active=True,
                complete=False,
                source="queue",
            )

        return list(apps.values())

    # ------------------------------------------------------------------ karar
    def rate_is_live(self, min_mbps: float = 1.0, within: float = 180.0) -> bool:
        """True when the launcher log shows a fresh download trace or it writes heavily."""
        log_fresh = (time.time() - self.log_last_download) <= within and self.log_state == "downloading"
        io_live = self.io_write_bps() > 2 * 1024 * 1024  # above 2 MB/s of writes
        return bool(log_fresh or io_live)

    def io_write_bps(self) -> float:
        return sum(v.get("write_bps", 0.0) for v in self.io.values())
