"""Decision engine: is the download really finished?

Design rule: NEVER shut down on a wrong signal.
  * Shutdowns are only possible after a *watched* download has been observed.
  * Every watched app must end up fully installed.
  * After the download stops, the state must stay calm for `confirm_seconds`.
  * If a watched download starts again during the countdown, the action is cancelled.

Selection model:
  * Every download that appears is added to the watch list automatically.
  * The user may untick a game ("ignore") - it then no longer gates the action.
  * Refresh re-scans and re-adds anything that was ignored earlier.

Phases:
  stopped / waiting / downloading / draining / ready / done / interrupted
"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field

from . import power
from .config import Config
from .epic import EpicApp, EpicSource
from .i18n import tr
from .steam import ACTIVE_WORDS, SteamApp, SteamSource
from .util import fmt_bytes


@dataclass
class Tracked:
    key: str
    label: str
    source: str
    first_seen: float
    last_active: float
    downloaded: int = 0
    total: int = 0
    complete: bool = False


@dataclass
class Status:
    phase: str = "waiting"
    detail_key: str = "detail.waiting"
    detail_params: dict = field(default_factory=dict)
    apps: list[dict] = field(default_factory=list)
    tracked: list[dict] = field(default_factory=list)
    countdown_left: float | None = None
    rate_mbps: float = 0.0
    io_bps: float = 0.0
    ts: float = 0.0
    steam_running: bool = False
    epic_running: bool = False
    armed: bool = False
    enabled: bool = True
    found_count: int = 0
    watching_count: int = 0
    ignored_count: int = 0

    @property
    def detail(self) -> str:
        return tr(self.detail_key, **self.detail_params)


class Detector:
    def __init__(self, cfg: Config, log_sink=None) -> None:
        self.cfg = cfg
        self._log_sink = log_sink
        self.steam = SteamSource()
        self.epic = EpicSource()
        self.enabled = True
        self.armed = False
        self.phase = "waiting"
        self.watched: set[str] = set()
        self.dismissed: set[str] = set()
        self.tracked: dict[str, Tracked] = {}
        self.drain_since: float | None = None
        self.countdown_until: float | None = None
        self._prev_bytes: dict[str, int] = {}
        self._lock = threading.RLock()
        self._last_note = 0.0
        self._drain_logged = False
        self._refresh_requested: str | bool = False
        self._missing_since: float | None = None
        self._auto_refresh_at = 0.0
        self.last_status = Status()
        self.last_action_key = "detail.stopped"
        self.last_action_params: dict = {}
        self._started_at = time.time()

    # ------------------------------------------------------------------ logging
    def log(self, key: str, level: str = "info", **params) -> None:
        """Emit a translatable log line. Only the key is stored, so switching
        language re-renders past lines too."""
        if self._log_sink:
            try:
                self._log_sink(key, params, level)
            except Exception:
                pass

    # ------------------------------------------------------------------ control
    def set_enabled(self, value: bool) -> None:
        with self._lock:
            self.enabled = bool(value)
            if not value:
                self._disarm("log.stopped")
            else:
                self.armed = False
                self.tracked.clear()
                self.watched.clear()
                self.dismissed.clear()
                self.drain_since = None
                self.countdown_until = None
                self._drain_logged = False
                self.phase = "waiting"
                self._started_at = time.time()
                self.last_action_key = "detail.waiting"
                self.last_action_params = {}
                self.log("log.watching")

    def cancel_shutdown(self) -> None:
        with self._lock:
            if self.phase == "ready":
                self.log("log.cancel_ok", "warn")
                self._disarm("log.cancel_ok")
            else:
                self.log("log.cancel_none", "warn")
                self._disarm("log.cancel_none")

    def set_watched(self, key: str, value: bool) -> None:
        """Tick/untick a game in the list."""
        with self._lock:
            if value:
                self.dismissed.discard(key)
                self.watched.add(key)
                if self.phase == "stopped":
                    self.enabled = True
            else:
                self.watched.discard(key)
                self.dismissed.add(key)
                tracked = self.tracked.pop(key, None)
                if tracked:
                    self.log("log.unwatched", name=tracked.label)
                else:
                    self.log("log.unwatched", name=key)

    def refresh(self) -> None:
        """Re-scan libraries and re-add downloads that were ignored before."""
        with self._lock:
            self.dismissed.clear()
            self._refresh_requested = "manual"

    def _disarm(self, reason_key: str, phase: str = "stopped", **params) -> None:
        self.enabled = False
        self.armed = False
        self.tracked.clear()
        self.watched.clear()
        self.drain_since = None
        self.countdown_until = None
        self._drain_logged = False
        self._missing_since = None
        self.phase = phase
        self.last_action_key = reason_key
        self.last_action_params = params

    # ------------------------------------------------------------------ step
    def step(self) -> Status:
        with self._lock:
            return self._step()

    def _step(self) -> Status:
        now = time.time()
        cfg = self.cfg

        # periodic re-scan so the list keeps itself up to date
        interval = float(cfg.get("auto_refresh_seconds") or 0)
        if interval > 0 and now >= self._auto_refresh_at:
            self._auto_refresh_at = now + interval
            self.steam.invalidate_libraries()
            if not self._refresh_requested:
                self._refresh_requested = "auto"

        steam_apps: list[SteamApp] = []
        epic_apps: list[EpicApp] = []

        if cfg.watch_steam and self.steam.available:
            try:
                steam_apps = self.steam.scan()
            except Exception as exc:  # noqa: BLE001 - one bad source must not kill the loop
                self.log("log.steam_scan_error", "warn", error=exc)
                steam_apps = []
        if cfg.watch_epic:
            try:
                epic_apps = self.epic.scan()
            except Exception as exc:  # noqa: BLE001
                self.log("log.epic_scan_error", "warn", error=exc)
                epic_apps = []

        # --- byte delta: hard evidence that data is still moving ----------
        for app in steam_apps:
            prev = self._prev_bytes.get(app.appid)
            app.gained = max(0, app.downloaded - prev) if prev is not None else 0
            self._prev_bytes[app.appid] = app.downloaded

        all_apps = list(steam_apps) + list(epic_apps)
        active_apps = [a for a in all_apps if a.active or (getattr(a, "gained", 0) > 512 * 1024 and not a.complete)]

        # --- auto-watch every download we have not been told to ignore ----
        added: list[str] = []
        newly_tracked: list[str] = []
        for app in active_apps:
            if app.key in self.dismissed or app.key in self.watched:
                continue
            self.watched.add(app.key)
            added.append(app.name)

        if self._refresh_requested:
            mode = self._refresh_requested
            self._refresh_requested = False
            if mode == "manual" or added:
                self.log("log.refresh", active=len(active_apps), added=len(added))

        for name in added:
            self.log("log.new_download", name=name)

        busy = [(a.key, a.name) for a in active_apps if a.key in self.watched]
        others = [a for a in active_apps if a.key not in self.watched]

        rate_mbps = self.steam.fresh_rate() if cfg.watch_steam else 0.0
        io_bps = (self.steam.io_write_bps() if cfg.watch_steam else 0.0) + (
            self.epic.io_write_bps() if cfg.watch_epic else 0.0
        )

        status = Status(
            ts=now,
            rate_mbps=rate_mbps,
            io_bps=io_bps,
            steam_running=bool(self.steam.io) if cfg.watch_steam else False,
            epic_running=bool(self.epic.io) if cfg.watch_epic else False,
            armed=self.armed,
            enabled=self.enabled,
            found_count=len(active_apps),
            watching_count=len(busy),
            ignored_count=len(others),
        )

        if not self.enabled:
            status.phase = self.phase if self.phase in ("done", "interrupted") else "stopped"
            status.detail_key = self.last_action_key
            status.detail_params = self.last_action_params
            status.apps = self._apps_view(all_apps, rate_mbps)
            self.last_status = status
            return status

        # --- remember every watched download -----------------------------
        if busy:
            if not self.armed:
                self.armed = True
                self._started_at = now
                self.log("log.download_detected", names=", ".join(name for _, name in busy))
            for key, name in busy:
                tracked = self.tracked.get(key)
                if tracked is None:
                    tracked = Tracked(
                        key=key,
                        label=name,
                        source=key.split(":")[0],
                        first_seen=now,
                        last_active=now,
                    )
                    self.tracked[key] = tracked
                    newly_tracked.append(name)
                tracked.last_active = now
            if newly_tracked:
                self.log("log.tracking", name=", ".join(newly_tracked))
            for app in steam_apps:
                tracked = self.tracked.get(app.key)
                if tracked:
                    tracked.downloaded = app.downloaded
                    tracked.total = app.total
            self.drain_since = None
            self.countdown_until = None
            self._drain_logged = False
            self._missing_since = None
            self.phase = "downloading"
        elif self.phase == "ready":
            pass  # countdown block below handles it
        elif self.armed and self.tracked:
            if self.drain_since is None:
                self.drain_since = now
                self.phase = "draining"
                if not self._drain_logged:
                    self._drain_logged = True
                    self.log("log.drain_started", seconds=int(cfg.confirm_seconds))
            if now - self.drain_since >= float(cfg.confirm_seconds):
                ok, key, params = self._verify(steam_apps, epic_apps, others)
                if ok:
                    self.phase = "ready"
                    self.countdown_until = now + float(cfg.delay_seconds)
                    names = ", ".join(t.label for t in self.tracked.values())
                    self.log("log.completed", names=names)
                    self.log("log.evidence", "ok", details=self._evidence(steam_apps))
                    self.log(
                        "log.action_in",
                        seconds=int(cfg.delay_seconds),
                        action=tr(f"action.{cfg.action}"),
                    )
                else:
                    self._note_missing(key, now)
                    self.drain_since = now
                    if now - self._last_note > 20:
                        self._last_note = now
                        self.log(key, "warn", **params)
        elif self.armed:
            # every download was un-ticked -> nothing gates the shutdown any more
            self.armed = False
            self.drain_since = None
            self.countdown_until = None
            self._drain_logged = False
            self.phase = "waiting"
            if not self.tracked:
                self.log("log.nothing_watched", "muted")
        else:
            self.phase = "waiting"

        # --- countdown / action ------------------------------------------
        if self.phase == "ready":
            if busy:
                self.countdown_until = None
                self.drain_since = None
                self._drain_logged = False
                self.phase = "downloading"
                self.log("log.resumed", "warn")
            elif self.countdown_until is not None and now >= self.countdown_until:
                # last line of defence: re-read everything from disk right now
                try:
                    fresh_steam = self.steam.scan() if (cfg.watch_steam and self.steam.available) else []
                    fresh_epic = self.epic.scan() if cfg.watch_epic else []
                except Exception:  # noqa: BLE001
                    fresh_steam, fresh_epic = steam_apps, epic_apps
                ok, key, params = self._verify(fresh_steam, fresh_epic, others)
                if ok:
                    self._execute_action()
                else:
                    self.countdown_until = None
                    self.drain_since = now
                    self._drain_logged = False
                    self.phase = "draining"
                    self.log("log.recheck_failed", "warn")
                    self.log(key, "warn", **params)

        status.phase = self.phase
        status.countdown_left = (
            max(0.0, self.countdown_until - now) if (self.phase == "ready" and self.countdown_until) else None
        )
        status.apps = self._apps_view(all_apps, rate_mbps)
        status.tracked = [
            {
                "key": t.key,
                "label": t.label,
                "source": t.source,
                "complete": self._tracked_complete(t, steam_apps, epic_apps),
                "downloaded": t.downloaded,
                "total": t.total,
            }
            for t in self.tracked.values()
        ]

        if self.phase == "draining" and self.drain_since:
            left = int(max(0, float(cfg.confirm_seconds) - (now - self.drain_since)))
            status.detail_key = "detail.draining"
            status.detail_params = {"seconds": left}
        elif self.phase == "downloading":
            if others:
                status.detail_key = "detail.active_others"
                status.detail_params = {"count": len(busy), "others": len(others)}
            else:
                status.detail_key = "detail.active"
                status.detail_params = {"count": len(busy)}
        elif self.phase == "ready":
            status.detail_key = "detail.ready"
            status.detail_params = {
                "seconds": int(status.countdown_left or 0),
                "action": tr(f"action.{cfg.action}"),
            }
        elif self.phase == "waiting":
            if active_apps and not any(a.key in self.watched for a in active_apps):
                status.detail_key = "detail.nowatch"
            else:
                status.detail_key = "detail.waiting"
        elif self.phase == "done":
            status.detail_key = self.last_action_key
            status.detail_params = self.last_action_params
        else:
            status.detail_key = "detail.stopped"

        self.last_status = status
        return status

    # ------------------------------------------------------------------ verify
    def _verify(self, steam_apps, epic_apps, others) -> tuple[bool, str, dict]:
        """Final, strict gate before acting."""
        if not self.tracked:
            return False, "verify.no_tracked", {}

        # 1) Is the transfer still alive? (only meaningful if nothing else is downloading)
        if not others and self.cfg.watch_steam and self.steam.rate_is_live(self.cfg.min_rate_mbps, within=90.0):
            return False, "verify.steam_rate", {"mbps": self.steam.last_rate_mbps}

        steam_by_id = {a.appid: a for a in steam_apps}
        epic_by_key = {a.key: a for a in epic_apps}

        # 2) Everything we watched must be fully installed now.
        for key, tracked in self.tracked.items():
            source, _, ident = key.partition(":")
            if source == "steam":
                app = steam_by_id.get(ident)
                if app is None:
                    return False, "verify.manifest_missing", {"name": tracked.label}
                if not app.complete:
                    return False, "verify.not_installed", {"name": tracked.label, "flags": app.flags}
                words = self.steam.logged_state(ident)
                if words and ("Fully Installed" not in words or set(words) & ACTIVE_WORDS):
                    return False, "verify.log_state", {
                        "name": tracked.label,
                        "state": ", ".join(words),
                    }
                if app.total > 0 and app.downloaded < app.total * 0.999:
                    return False, "verify.bytes_missing", {
                        "name": tracked.label,
                        "got": fmt_bytes(app.downloaded),
                        "total": fmt_bytes(app.total),
                    }
            elif source == "epic":
                app = epic_by_key.get(key)
                if app is None:
                    return False, "verify.epic_manifest_missing", {"name": tracked.label}
                if app.incomplete:
                    return False, "verify.epic_downloading", {"name": tracked.label}
            else:
                return False, "verify.unknown_source", {"key": key}

        # 3) A watched app may not still be active.
        for app in steam_apps:
            if app.active and app.appid in {k.partition(":")[2] for k in self.tracked}:
                return False, "verify.still_active", {"name": app.name}
        for app in epic_apps:
            if app.active and app.key in self.tracked:
                return False, "verify.still_active", {"name": app.name}

        return True, "verify.ok", {}

    @staticmethod
    def _tracked_complete(tracked: Tracked, steam_apps, epic_apps) -> bool:
        source, _, ident = tracked.key.partition(":")
        if source == "steam":
            return any(a.appid == ident and a.complete for a in steam_apps)
        if source == "epic":
            return any(a.key == tracked.key and a.complete for a in epic_apps)
        return False

    def _evidence(self, steam_apps) -> str:
        """Human-readable proof of completion, written to the event log."""
        steam_by_id = {a.appid: a for a in steam_apps}
        parts: list[str] = []
        for key, tracked in self.tracked.items():
            source, _, ident = key.partition(":")
            if source == "steam":
                app = steam_by_id.get(ident)
                if not app:
                    continue
                state = ", ".join(self.steam.logged_state(ident)) or "n/a"
                parts.append(
                    f"{app.name}: flags={app.flags}, "
                    f"{fmt_bytes(app.downloaded)}/{fmt_bytes(app.total)}, log='{state}'"
                )
            else:
                parts.append(f"{tracked.label}: Epic manifest complete")
        return " | ".join(parts) or "ok"

    def _note_missing(self, key: str, now: float) -> None:
        """Steam/Epic data vanished mid-download: stop verifying after five minutes."""
        if key not in ("verify.manifest_missing", "verify.epic_manifest_missing"):
            self._missing_since = None
            return
        if self._missing_since is None:
            self._missing_since = now
        elif now - self._missing_since > 300:
            self.log("log.interrupted_missing", "error")
            self._disarm("log.interrupted_missing", phase="interrupted")

    # ------------------------------------------------------------------ action
    def _execute_action(self) -> None:
        action = str(self.cfg.action)
        label = tr(f"action.{action}")
        self.countdown_until = None

        if action == "test":
            self.phase = "done"
            self.last_action_key = "log.test_mode"
            self.last_action_params = {"action": label}
            self.log(self.last_action_key, "warn", **self.last_action_params)
            self.enabled = False
            return

        self.phase = "done"
        self.last_action_key = "log.executing"
        self.last_action_params = {"action": label}
        self.log(self.last_action_key, "warn", **self.last_action_params)
        try:
            if self.cfg.stop_steam_on_action:
                _kill("steam.exe")
            power.execute(action)
        except Exception as exc:  # noqa: BLE001
            self.log("log.action_failed", "error", error=exc)
            self.last_action_key = "log.action_failed"
            self.last_action_params = {"error": exc}
        self.enabled = False

    # ------------------------------------------------------------------ view
    def _apps_view(self, all_apps, rate_mbps: float, active_only: bool = True) -> list[dict]:
        view: list[dict] = []
        for app in all_apps:
            is_steam = isinstance(app, SteamApp)
            watched = app.key in self.watched
            if active_only and not (app.active or watched or app.key in self.tracked):
                continue
            rate = rate_mbps * 1_000_000 / 8 if (is_steam and app.active and app.key in self.watched and rate_mbps > 0) else 0.0
            eta = None
            remaining = 0
            shown_downloaded = app.downloaded if is_steam else 0
            if is_steam:
                remaining = max(0, app.total - app.downloaded)
                eta = (remaining / rate) if (rate > 0 and remaining > 0) else None
            view.append(
                {
                    "key": app.key,
                    "source": "Steam" if is_steam else "Epic",
                    "name": app.name if is_steam else app.name,
                    "progress": app.progress if is_steam else None,
                    "downloaded": shown_downloaded if is_steam else 0,
                    "total": app.total if is_steam else 0,
                    "size_on_disk": app.size_on_disk if is_steam else app.install_size,
                    "rate_bps": rate,
                    "eta": eta,
                    "active": bool(app.active),
                    "complete": bool(app.complete),
                    "watched": watched,
                    "note_key": self._note_key(app, rate, is_steam),
                }
            )
        view.sort(key=lambda v: (not v["active"], not v["watched"], v["name"].lower()))
        return view

    @staticmethod
    def _note_key(app, rate: float, is_steam: bool) -> str:
        if is_steam:
            if app.active and not app.complete and rate == 0:
                return "row.queued"
            return ""
        return "row.no_progress" if app.active else ""

    # ------------------------------------------------------------------ loop
    def run(self, on_status, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                on_status(self.step())
            except Exception as exc:  # noqa: BLE001
                self.log("log.unexpected", "error", error=exc)
                time.sleep(2)
            stop_event.wait(max(0.5, float(self.cfg.poll_seconds)))


def _kill(exe: str) -> None:
    try:
        subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True, timeout=10)
    except Exception:  # noqa: BLE001
        pass
