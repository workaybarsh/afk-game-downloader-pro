"""Steam download detection.

Three independent pieces of evidence are combined:
  1) <Steam>\\logs\\content_log.txt -> the real state machine (primary evidence)
  2) steamapps\\appmanifest_*.acf -> StateFlags + downloaded/total bytes
  3) steam.exe process IO activity (supporting evidence)

Rule: an app only counts as COMPLETE when its appmanifest says "Fully Installed"
with no "Update Required"-style bits left. A delayed update ("Update delayed")
is not a download and must not block shutdown.
"""

from __future__ import annotations

import re
import time
import winreg
from dataclasses import dataclass, field
from pathlib import Path

from .procs import ProcessActivity
from .vdf import parse_vdf_file

# --- StateFlags bits (Steam) ---------------------------------------------------
FLAG_FULLY_INSTALLED = 0x4
FLAG_UPDATE_REQUIRED = 0x2
# Bits that can mean "a download/install is still in progress"
FLAG_UNSETTLED = (
    0x2       # Update Required
    | 0x8     # Update Queued
    | 0x10    # Update Optional
    | 0x20    # Files Missing
    | 0x100   # Update Running
    | 0x200   # Update Paused
    | 0x400   # Update Started
    | 0x4000  # Validating
    | 0x8000  # Adding Files
    | 0x10000 # Preallocating
    | 0x20000 # Downloading
    | 0x40000 # Staging
    | 0x80000 # Committing
)

# State words found in content_log.txt
ACTIVE_WORDS = {
    "Update Queued",
    "Update Running",
    "Update Started",
    "Update Paused",
    "Downloading",
    "Staging",
    "Committing",
    "Preallocating",
    "Validating",
    "Reconfiguring",
    "Adding Files",
    "Prefetching Info",
}
DONE_WORDS = {"Fully Installed"}

RE_STATE = re.compile(r"AppID (\d+) state changed : (.*)$")
RE_UPDATE = re.compile(r"AppID (\d+) App update changed : (.*)$")
RE_STARTED = re.compile(r"AppID (\d+) update started : download (\d+)/(\d+)")
RE_RATE = re.compile(r"Current download rate: ([\d.]+) Mbps")
RE_DELAYED = re.compile(r"\(Update delayed for \d+ secs\)")

COMMON_ROOTS = [
    Path(r"C:\Program Files (x86)\Steam"),
    Path(r"C:\Program Files\Steam"),
    Path(r"D:\Steam"),
    Path(r"E:\Steam"),
]


@dataclass
class SteamApp:
    appid: str
    name: str
    library: str
    flags: int = 0
    downloaded: int = 0
    total: int = 0
    size_on_disk: int = 0
    state_words: tuple[str, ...] = ()
    delayed: bool = False
    active: bool = False
    complete: bool = False
    gained: int = 0
    manifest_time: float = 0.0

    @property
    def key(self) -> str:
        return f"steam:{self.appid}"

    @property
    def progress(self) -> float:
        if self.total > 0:
            return max(0.0, min(1.0, self.downloaded / self.total))
        return 1.0 if self.complete else 0.0

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.downloaded)


def find_steam_root() -> Path | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            value, _ = winreg.QueryValueEx(key, "SteamPath")
            candidate = Path(value)
            if (candidate / "steamapps").is_dir():
                return candidate
    except OSError:
        pass
    for candidate in COMMON_ROOTS:
        if (candidate / "steamapps").is_dir():
            return candidate
    return None


class SteamSource:
    label = "Steam"

    def __init__(self) -> None:
        self.root = find_steam_root()
        self.log_path = (self.root / "logs" / "content_log.txt") if self.root else None
        self._offset = 0
        self._rest = ""
        self._states: dict[str, set[str]] = {}
        self._runtime: dict[str, set[str]] = {}
        self._delayed: set[str] = set()
        self._app_bytes: dict[str, tuple[int, int]] = {}
        self.last_rate_mbps: float = 0.0
        self.last_rate_time: float = 0.0
        self.log_mtime: float = 0.0
        self._lib_cache: tuple[float, list[Path]] = (0.0, [])
        self.activity = ProcessActivity()
        self.io: dict[str, dict] = {}

    # ------------------------------------------------------------------ helpers
    @property
    def available(self) -> bool:
        return self.root is not None

    def running(self) -> bool:
        return bool(self.activity.sample({"steam.exe"}))

    def libraries(self) -> list[Path]:
        now = time.time()
        if self._lib_cache[1] and now - self._lib_cache[0] < 60:
            return self._lib_cache[1]
        libs: list[Path] = []
        if self.root:
            libs.append(self.root)
        for vdf in (
            (self.root / "config" / "libraryfolders.vdf") if self.root else None,
            (self.root / "steamapps" / "libraryfolders.vdf") if self.root else None,
        ):
            if vdf and vdf.exists():
                data = parse_vdf_file(vdf)
                node = data.get("libraryfolders") or data.get("LibraryFolders") or {}
                for value in node.values():
                    if isinstance(value, dict):
                        path = value.get("path")
                        if path:
                            libs.append(Path(path))
                break
        unique: list[Path] = []
        for lib in libs:
            try:
                if (lib / "steamapps").is_dir() and lib not in unique:
                    unique.append(lib)
            except OSError:
                continue
        self._lib_cache = (now, unique)
        return unique

    def invalidate_libraries(self) -> None:
        """Force libraryfolders.vdf to be re-read on the next scan."""
        self._lib_cache = (0.0, [])

    # ------------------------------------------------------------------ log tailing
    def _reset_log(self) -> None:
        self._offset = 0
        self._rest = ""
        self._states.clear()
        self._runtime.clear()
        self._delayed.clear()
        self._app_bytes.clear()
        if not self.log_path or not self.log_path.exists():
            return
        try:
            size = self.log_path.stat().st_size
            with self.log_path.open("rb") as handle:
                handle.seek(max(0, size - 300_000))
                chunk = handle.read()
            self._offset = size
            self._consume(chunk.decode("utf-8", "replace"))
        except OSError:
            pass

    def poll_log(self) -> None:
        if not self.log_path:
            return
        try:
            stat = self.log_path.stat()
        except OSError:
            return
        self.log_mtime = stat.st_mtime
        if stat.st_size < self._offset:
            self._reset_log()
            return
        if stat.st_size == self._offset:
            return
        try:
            with self.log_path.open("rb") as handle:
                handle.seek(self._offset)
                chunk = handle.read(stat.st_size - self._offset)
            self._offset += len(chunk)
        except OSError:
            return
        self._consume(chunk.decode("utf-8", "replace"))

    def _consume(self, text: str) -> None:
        text = self._rest + text
        if not text.endswith("\n"):
            cut = text.rfind("\n")
            if cut == -1:
                self._rest = text
                return
            self._rest = text[cut + 1:]
            text = text[:cut + 1]
        else:
            self._rest = ""

        for line in text.splitlines():
            rate = RE_RATE.search(line)
            if rate:
                try:
                    self.last_rate_mbps = float(rate.group(1))
                    self.last_rate_time = time.time()
                except ValueError:
                    pass
                continue

            started = RE_STARTED.search(line)
            if started:
                appid = started.group(1)
                self._app_bytes[appid] = (int(started.group(2)), int(started.group(3)))
                continue

            state = RE_STATE.search(line)
            if state:
                appid = state.group(1)
                words = {
                    w.strip()
                    for w in state.group(2).split(",")
                    if w.strip() and not w.strip().startswith("(")
                }
                self._states[appid] = words
                if RE_DELAYED.search(line):
                    self._delayed.add(appid)
                else:
                    self._delayed.discard(appid)
                continue

            update = RE_UPDATE.search(line)
            if update:
                appid = update.group(1)
                words = {
                    w.strip()
                    for w in update.group(2).split(",")
                    if w.strip() and not w.strip().startswith("(")
                }
                self._runtime[appid] = words

    # ------------------------------------------------------------------ scanning
    def scan(self) -> list[SteamApp]:
        self.poll_log()
        self.io = self.activity.sample({"steam.exe"})
        apps: list[SteamApp] = []
        if not self.root:
            return apps
        for lib in self.libraries():
            steamapps = lib / "steamapps"
            try:
                manifests = sorted(steamapps.glob("appmanifest_*.acf"))
            except OSError:
                continue
            for manifest in manifests:
                data = parse_vdf_file(manifest)
                state = data.get("AppState")
                if not isinstance(state, dict):
                    continue
                appid = str(state.get("appid") or manifest.stem.split("_")[-1])
                try:
                    flags = int(state.get("StateFlags") or 0)
                except (TypeError, ValueError):
                    flags = 0
                try:
                    downloaded = int(state.get("BytesDownloaded") or 0)
                except (TypeError, ValueError):
                    downloaded = 0
                try:
                    total = int(state.get("BytesToDownload") or 0)
                except (TypeError, ValueError):
                    total = 0
                try:
                    size_on_disk = int(state.get("SizeOnDisk") or 0)
                except (TypeError, ValueError):
                    size_on_disk = 0
                try:
                    mtime = manifest.stat().st_mtime
                except OSError:
                    mtime = 0.0

                words = tuple(sorted(self._states.get(appid, set()) | self._runtime.get(appid, set())))
                if downloaded == 0 and total == 0:
                    hint = self._app_bytes.get(appid)
                    if hint:
                        downloaded, total = hint

                app = SteamApp(
                    appid=appid,
                    name=str(state.get("name") or appid),
                    library=str(lib),
                    flags=flags,
                    downloaded=downloaded,
                    total=total,
                    size_on_disk=size_on_disk,
                    state_words=words,
                    delayed=appid in self._delayed,
                    manifest_time=mtime,
                )
                app.active = self._is_active(app)
                app.complete = self._is_complete(app)
                apps.append(app)
        return apps

    # ------------------------------------------------------------------ decisions
    def _is_active(self, app: SteamApp) -> bool:
        words = set(app.state_words)
        has_active_word = bool(words & ACTIVE_WORDS)

        if app.delayed and not (words & {"Update Running", "Downloading", "Staging"}):
            return False

        if has_active_word:
            # the log says active; the manifest must agree that it is not settled
            return bool(app.flags & FLAG_UNSETTLED) or app.downloaded < app.total

        # no log entry / passive -> trust the manifest bits
        if app.flags & FLAG_UNSETTLED:
            # "Update Required" alone on an installed app is usually a delayed update
            if app.flags == (FLAG_FULLY_INSTALLED | FLAG_UPDATE_REQUIRED):
                return False
            return True
        return False

    @staticmethod
    def _is_complete(app: SteamApp) -> bool:
        if not (app.flags & FLAG_FULLY_INSTALLED):
            return False
        if app.flags & (FLAG_UPDATE_REQUIRED | 0x8 | 0x100 | 0x400):
            return False
        return True

    def logged_state(self, appid: str) -> tuple[str, ...]:
        """Last state words Steam logged for this app (empty if unknown)."""
        return tuple(sorted(self._states.get(appid, set())))

    def rate_is_live(self, min_mbps: float = 1.0, within: float = 150.0) -> bool:
        if self.last_rate_time <= 0:
            return False
        return (time.time() - self.last_rate_time) <= within and self.last_rate_mbps >= min_mbps

    def fresh_rate(self, within: float = 150.0) -> float:
        if self.last_rate_time and (time.time() - self.last_rate_time) <= within:
            return self.last_rate_mbps
        return 0.0

    def io_write_bps(self) -> float:
        return sum(v.get("write_bps", 0.0) for v in self.io.values())
