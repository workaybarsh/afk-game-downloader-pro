"""Tkinter UI: status banner, download rows, event log and controls.

Language can be switched at runtime; nothing needs a restart.
"""

from __future__ import annotations

import ctypes
import queue
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import messagebox, ttk

from . import __version__, i18n, power
from .config import ACTION_ORDER, Config
from .detector import Detector, Status
from .i18n import tr
from .util import clock, fmt_bytes, fmt_duration, fmt_speed, pct

BG = "#0d1117"
CARD = "#161b22"
CARD2 = "#21262d"
BORDER = "#30363d"
FG = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#2f81f7"
GREEN = "#3fb950"
AMBER = "#d29922"
RED = "#f85149"

FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI Semibold", 10)
FONT_SM = ("Segoe UI", 9)
FONT_H1 = ("Segoe UI Semibold", 16)
FONT_PHASE = ("Segoe UI Semibold", 13)

PHASE_COLORS = {
    "stopped": (CARD2, MUTED),
    "waiting": (CARD2, ACCENT),
    "downloading": ("#123a63", "#9ecbff"),
    "draining": ("#3d2f0a", AMBER),
    "ready": ("#0f3d1f", "#7ee787"),
    "done": ("#0f3d1f", "#7ee787"),
    "interrupted": ("#4a1416", "#ff9c96"),
}


def work_area(width: int, height: int) -> tuple[int, int, int, int]:
    """Usable desktop area (taskbar excluded), falling back to the whole screen."""
    try:
        rect = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 200 and h > 200:
                return rect.left, rect.top, w, h
    except Exception:  # noqa: BLE001
        pass
    return 0, 0, width, height


class AppUI:
    def __init__(self) -> None:
        self.cfg = Config()
        # Steam and Epic are always watched; no per-source switch in the UI
        self.cfg["watch_steam"] = True
        self.cfg["watch_epic"] = True
        i18n.set_lang(str(self.cfg.get("language") or "en"))
        self.detector = Detector(self.cfg, self._log_sink)
        self.events: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.rows: dict[str, dict] = {}
        self.last_status: Status | None = None
        self.log_entries: list[tuple[float, str, str, dict]] = []

        self.root = tk.Tk()
        self.root.configure(bg=BG)
        self._left, self._top, self._area_w, self._area_h = work_area(
            self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        )
        self._compact = self._area_h < 700
        self.root.geometry(self.cfg.get("window_geometry") or self._default_geometry())
        self.root.minsize(680, 520)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_window_icon()

        self._build_styles()
        self._build_header()
        self._build_banner()
        self._build_apps_area()
        self._build_controls()
        self._build_log()
        self._apply_language()

        self._start_worker()
        self.root.after(120, self._drain_queue)
        self._intro()

    # ------------------------------------------------------------------ layout
    def _set_window_icon(self) -> None:
        bases = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bases.append(Path(meipass) / "assets")
        bases.append(Path(__file__).resolve().parent.parent / "assets")

        for base in bases:
            ico = base / "app.ico"
            try:
                if ico.is_file():
                    self.root.iconbitmap(default=str(ico))
                    break
            except tk.TclError:
                continue

        # a proper multi-size photo icon keeps the taskbar crisp too
        for size in (128, 64, 32):
            for base in bases:
                png = base / f"icon_{size}.png"
                try:
                    if png.is_file():
                        self._icon_photo = tk.PhotoImage(file=str(png))
                        self.root.iconphoto(True, self._icon_photo)
                        return
                except tk.TclError:
                    continue

    def _default_geometry(self) -> str:
        width = int(min(900, max(680, self._area_w - 24)))
        height = int(min(800, max(520, self._area_h - 12)))
        x = int(self._left + (self._area_w - width) / 2)
        y = int(self._top + max(0, (self._area_h - height) / 2))
        return f"{width}x{height}+{x}+{y}"

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Bar.Horizontal.TProgressbar",
            troughcolor=CARD2,
            background=ACCENT,
            bordercolor=CARD2,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=8,
        )
        style.configure(
            "BarDone.Horizontal.TProgressbar",
            troughcolor=CARD2,
            background=GREEN,
            bordercolor=CARD2,
            lightcolor=GREEN,
            darkcolor=GREEN,
            thickness=8,
        )
        style.configure(
            "TCombobox",
            fieldbackground=CARD2,
            background=CARD2,
            foreground=FG,
            arrowcolor=FG,
            borderwidth=0,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", CARD2)],
            foreground=[("readonly", FG)],
            selectbackground=[("readonly", CARD2)],
        )
        style.configure("Vertical.TScrollbar", background=CARD2, troughcolor=BG, arrowcolor=MUTED, borderwidth=0)

    def _build_header(self) -> None:
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=16, pady=(12 if self._compact else 16, 6))
        self.lbl_title = tk.Label(head, text="AFK Game Downloader Pro", bg=BG, fg=FG, font=FONT_H1)
        self.lbl_title.pack(side="left")

        self.btn_lang = tk.Button(
            head,
            text="TR",
            command=self._on_lang,
            bg=CARD2,
            fg=MUTED,
            activebackground=BORDER,
            activeforeground=FG,
            relief="flat",
            font=("Segoe UI Semibold", 9),
            padx=8,
            pady=2,
            cursor="hand2",
        )
        self.btn_lang.pack(side="right", padx=(8, 0))

        self.lbl_sub = tk.Label(head, text="", bg=BG, fg=MUTED, font=FONT_SM)
        self.lbl_sub.pack(side="right", pady=(4, 0))

    def _build_banner(self) -> None:
        self.banner = tk.Frame(self.root, bg=CARD2, highlightthickness=1, highlightbackground=BORDER)
        self.banner.pack(fill="x", padx=16, pady=(0, 8 if self._compact else 12))
        pad = 10 if self._compact else 14
        self.banner_inner = tk.Frame(self.banner, bg=CARD2)
        self.banner_inner.pack(fill="x", padx=16, pady=pad)
        self.lbl_phase = tk.Label(
            self.banner_inner, text="", bg=CARD2, fg=MUTED, font=FONT_PHASE, anchor="w"
        )
        self.lbl_phase.pack(fill="x")
        self.lbl_detail = tk.Label(
            self.banner_inner, text="", bg=CARD2, fg=MUTED, font=FONT, anchor="w", justify="left"
        )
        self.lbl_detail.pack(fill="x", pady=(3, 0))

    def _build_apps_area(self) -> None:
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        bar = tk.Frame(wrap, bg=BG)
        bar.pack(fill="x", pady=(0, 6))
        self.lbl_found = tk.Label(bar, text="", bg=BG, fg=MUTED, font=FONT_SM)
        self.lbl_found.pack(side="left")

        self.btn_refresh = tk.Button(
            bar,
            text="",
            command=self._on_refresh,
            bg=CARD2,
            fg=FG,
            activebackground=BORDER,
            activeforeground=FG,
            relief="flat",
            font=FONT_SM,
            padx=10,
            pady=2,
            cursor="hand2",
        )
        self.btn_refresh.pack(side="right")

        body = tk.Frame(wrap, bg=BG)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body, bg=BG, highlightthickness=0, height=120)
        self.scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        self.apps_inner = tk.Frame(self.canvas, bg=BG)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")
        self._canvas_window = self.canvas.create_window((0, 0), window=self.apps_inner, anchor="nw")
        self.apps_inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._canvas_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

        self.lbl_empty = tk.Label(
            self.apps_inner, text="", bg=BG, fg=MUTED, font=FONT, justify="left", anchor="w"
        )
        self.lbl_empty.pack(fill="x", pady=8)

    def _build_controls(self) -> None:
        box = tk.Frame(self.root, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        box.pack(fill="x", padx=16, pady=(0, 8))
        grid = tk.Frame(box, bg=CARD)
        grid.pack(fill="x", padx=12, pady=10 if self._compact else 12)

        row1 = tk.Frame(grid, bg=CARD)
        row1.pack(fill="x")
        self.lbl_when = tk.Label(row1, text="", bg=CARD, fg=FG, font=FONT)
        self.lbl_when.pack(side="left")

        self.cmb_action = ttk.Combobox(row1, values=[], state="readonly", width=24, font=FONT)
        self.cmb_action.pack(side="left", padx=(8, 10))
        self.cmb_action.bind("<<ComboboxSelected>>", self._on_action_change)

        self.lbl_countdown = tk.Label(row1, text="", bg=CARD, fg=MUTED, font=FONT_SM)
        self.lbl_countdown.pack(side="left", padx=(4, 4))
        self.spn_delay = self._spin(row1, 0, 3600, int(self.cfg.get("delay_seconds")), self._on_delay_change)
        self.spn_delay.pack(side="left")
        self.lbl_sec1 = tk.Label(row1, text="", bg=CARD, fg=MUTED, font=FONT_SM)
        self.lbl_sec1.pack(side="left", padx=(4, 12))

        self.lbl_verify = tk.Label(row1, text="", bg=CARD, fg=MUTED, font=FONT_SM)
        self.lbl_verify.pack(side="left", padx=(4, 4))
        self.spn_confirm = self._spin(row1, 30, 3600, int(self.cfg.get("confirm_seconds")), self._on_confirm_change)
        self.spn_confirm.pack(side="left")
        self.lbl_sec2 = tk.Label(row1, text="", bg=CARD, fg=MUTED, font=FONT_SM)
        self.lbl_sec2.pack(side="left", padx=(4, 0))

        row2 = tk.Frame(grid, bg=CARD)
        row2.pack(fill="x", pady=(8 if self._compact else 10, 0))


        self.btn_kill = self._button(row2, self._on_kill_now, CARD2, RED, FONT_SM)
        self.btn_kill.pack(side="right")
        self.btn_cancel = self._button(row2, self._on_cancel, CARD2, AMBER, FONT_B)
        self.btn_cancel.pack(side="right", padx=(0, 6))
        self.btn_stop = self._button(row2, lambda: self.detector.set_enabled(False), CARD2, FG, FONT_B)
        self.btn_stop.pack(side="right", padx=(0, 6))
        self.btn_start = self._button(row2, self._on_start, ACCENT, "white", FONT_B)
        self.btn_start.pack(side="right", padx=(0, 6))

    def _build_log(self) -> None:
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="x", padx=16, pady=(0, 4))
        self.log_panel = wrap
        header = tk.Frame(wrap, bg=BG)
        header.pack(fill="x")
        self.btn_log = tk.Button(
            header,
            text="",
            command=self._toggle_log,
            bg=BG,
            fg=MUTED,
            activebackground=BG,
            activeforeground=FG,
            relief="flat",
            bd=0,
            padx=0,
            pady=0,
            font=FONT_SM,
            cursor="hand2",
            anchor="w",
        )
        self.btn_log.pack(side="left")
        self.lbl_meta = tk.Label(header, text="", bg=BG, fg=MUTED, font=FONT_SM)
        self.lbl_meta.pack(side="right")

        log_wrap = tk.Frame(wrap, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        log_wrap.pack(fill="x", pady=(4, 0))
        self.log_body = log_wrap
        self.txt_log = tk.Text(
            log_wrap,
            height=5 if self._compact else 8,
            bg=CARD,
            fg=FG,
            font=("Consolas", 9),
            relief="flat",
            wrap="word",
            insertbackground=FG,
            padx=10,
            pady=6,
            state="disabled",
        )
        log_scroll = ttk.Scrollbar(log_wrap, orient="vertical", command=self.txt_log.yview, style="Vertical.TScrollbar")
        self.txt_log.configure(yscrollcommand=log_scroll.set)
        self.txt_log.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        for tag, color in (
            ("info", FG),
            ("muted", MUTED),
            ("warn", AMBER),
            ("error", RED),
            ("ok", GREEN),
            ("time", "#6e7681"),
        ):
            self.txt_log.tag_configure(tag, foreground=color)

    # ------------------------------------------------------------------ helpers
    def _spin(self, parent, lo: int, hi: int, value: int, cmd) -> tk.Spinbox:
        spn = tk.Spinbox(
            parent,
            from_=lo,
            to=hi,
            width=5,
            bg=CARD2,
            fg=FG,
            buttonbackground=CARD2,
            insertbackground=FG,
            relief="flat",
            font=FONT_SM,
            justify="center",
            command=cmd,
        )
        spn.delete(0, "end")
        spn.insert(0, str(value))
        spn.bind("<FocusOut>", cmd)
        spn.bind("<Return>", cmd)
        return spn

    def _check(self, parent, var: tk.BooleanVar, cmd) -> tk.Checkbutton:
        return tk.Checkbutton(
            parent,
            text="",
            variable=var,
            command=cmd,
            bg=CARD,
            fg=FG,
            activebackground=CARD,
            activeforeground=FG,
            selectcolor=CARD2,
            font=FONT_SM,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )

    def _button(self, parent, cmd, bg: str, fg: str, font) -> tk.Button:
        return tk.Button(
            parent,
            text="",
            command=cmd,
            bg=bg,
            fg=fg,
            activebackground=BORDER,
            activeforeground=fg,
            relief="flat",
            font=font,
            padx=12,
            pady=4,
            cursor="hand2",
        )

    def _on_wheel(self, event) -> None:
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ language
    def _apply_language(self) -> None:
        self.root.title(f"{tr('ui.title')} v{__version__}")
        self.lbl_sub.configure(text=tr("ui.subtitle", version=__version__))
        self.btn_lang.configure(text=tr("ui.lang_button"))
        self.lbl_when.configure(text=tr("ui.when_finish"))
        self.lbl_countdown.configure(text=tr("ui.countdown"))
        self.lbl_sec1.configure(text=tr("ui.sec"))
        self.lbl_verify.configure(text=tr("ui.verify"))
        self.lbl_sec2.configure(text=tr("ui.sec"))
        self.btn_start.configure(text=tr("ui.btn_start"))
        self.btn_stop.configure(text=tr("ui.btn_stop"))
        self.btn_cancel.configure(text=tr("ui.btn_cancel"))
        self.btn_kill.configure(text=tr("ui.btn_kill"))
        self.btn_refresh.configure(text=tr("ui.refresh"))
        self._apply_log_visibility()
        if getattr(self, "lbl_empty", None) is not None:
            self.lbl_empty.configure(text=tr("ui.empty"))

        values = [tr(f"action.{a}") for a in ACTION_ORDER]
        self.cmb_action.configure(values=values)
        current = self.cfg.get("action", "shutdown")
        self.cmb_action.current(ACTION_ORDER.index(current) if current in ACTION_ORDER else 0)

        self._render_log()
        if self.last_status:
            self._render_status(self.last_status)

    def _on_lang(self) -> None:
        self.cfg["language"] = i18n.toggle_lang()
        self.cfg.save()
        self._apply_language()

    # ------------------------------------------------------------------ events
    def _on_action_change(self, _event=None) -> None:
        index = self.cmb_action.current()
        if 0 <= index < len(ACTION_ORDER):
            self.cfg["action"] = ACTION_ORDER[index]
            self.cfg.save()

    def _on_delay_change(self, _event=None) -> None:
        try:
            self.cfg["delay_seconds"] = max(0, int(float(self.spn_delay.get())))
        except (ValueError, tk.TclError):
            return
        self.cfg.save()

    def _on_confirm_change(self, _event=None) -> None:
        try:
            self.cfg["confirm_seconds"] = max(30, int(float(self.spn_confirm.get())))
        except (ValueError, tk.TclError):
            return
        self.cfg.save()

    def _on_start(self) -> None:
        self.detector.set_enabled(True)

    def _on_cancel(self) -> None:
        self.detector.cancel_shutdown()

    def _on_refresh(self) -> None:
        """Re-scan the libraries and pull in downloads that were ignored."""
        self.detector.refresh()

    def _toggle_log(self) -> None:
        self.cfg["show_log"] = not bool(self.cfg.get("show_log", False))
        self.cfg.save()
        self._apply_log_visibility()

    def _apply_log_visibility(self) -> None:
        visible = bool(self.cfg.get("show_log", False))
        # only the log body is hidden; the header (and its toggle button) always stays
        if visible:
            if self.log_body.winfo_manager() != "pack":
                self.log_body.pack(fill="x", pady=(4, 0))
        else:
            self.log_body.pack_forget()
        arrow = "▾" if visible else "▸"
        self.btn_log.configure(text=f"{arrow}  {tr('ui.event_log')}", fg=MUTED if not visible else "#6e7681")

    def _on_kill_now(self) -> None:
        action = str(self.cfg.get("action", "shutdown"))
        if action == "test":
            action = "shutdown"
        label = tr(f"action.{action}")
        if not messagebox.askyesno(
            tr("ui.confirm_kill_title"),
            tr("ui.confirm_kill_body", action=label.lower()),
        ):
            return
        try:
            power.execute(action)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(tr("ui.error_title"), tr("ui.kill_failed", error=exc))

    def _on_close(self) -> None:
        status = self.last_status
        if status and status.phase == "ready":
            if not messagebox.askyesno(
                tr("ui.confirm_close_title"),
                tr("ui.confirm_close_body", seconds=int(status.countdown_left or 0)),
            ):
                return
        # Closing the window ends everything: the watcher thread stops with the
        # process and the countdown lives in this process, so no shutdown can
        # happen afterwards.
        self.detector.set_enabled(False)
        self.stop_event.set()
        if self.root.state() == "normal":
            self.cfg["window_geometry"] = self.root.geometry()
        self.cfg.save()
        self.root.destroy()

    # ------------------------------------------------------------------ worker
    def _start_worker(self) -> None:
        self.worker = threading.Thread(
            target=lambda: self.detector.run(self._status_sink, self.stop_event),
            daemon=True,
            name="afkdl-detector",
        )
        self.worker.start()

    def _status_sink(self, status: Status) -> None:
        self.events.put(("status", status))

    def _log_sink(self, key: str, params: dict, level: str = "info") -> None:
        self.events.put(("log", key, params, level))

    def _intro(self) -> None:
        det = self.detector
        self.detector.log("log.app_started")
        self.detector.log("log.steam_root", path=str(det.steam.root or "—"))
        self.detector.log("log.steam_libs", paths=", ".join(str(p) for p in det.steam.libraries()) or "—")
        self.detector.log("log.epic_found" if det.epic.available else "log.epic_missing")

    def _drain_queue(self) -> None:
        try:
            while True:
                item = self.events.get_nowait()
                if item[0] == "status":
                    self._render_status(item[1])
                elif item[0] == "log":
                    _, key, params, level = item
                    entry = (time.time(), level, key, params)
                    self.log_entries.append(entry)
                    self._append_log_entry(entry)
        except queue.Empty:
            pass
        self.root.after(120, self._drain_queue)

    # ------------------------------------------------------------------ render
    def _render_status(self, status: Status) -> None:
        self.last_status = status
        bg, fg = PHASE_COLORS.get(status.phase, (CARD2, MUTED))
        for widget in (self.banner, self.banner_inner):
            widget.configure(bg=bg)
        self.banner.configure(highlightbackground=bg)
        self.lbl_phase.configure(text=tr(f"phase.{status.phase}"), fg=fg, bg=bg)
        self.lbl_detail.configure(text=status.detail, fg=fg, bg=bg)

        if status.enabled:
            self.btn_start.configure(state="disabled", bg=CARD2, disabledforeground=MUTED)
            self.btn_stop.configure(state="normal", fg=FG)
        else:
            self.btn_start.configure(state="normal", bg=ACCENT)
            self.btn_stop.configure(state="disabled", disabledforeground=MUTED)

        if status.phase == "ready":
            self.btn_cancel.configure(state="normal", fg=AMBER)
        else:
            self.btn_cancel.configure(state="disabled", disabledforeground=MUTED)

        self._render_apps(status.apps)
        if status.found_count:
            self.lbl_found.configure(
                text=tr("ui.found", count=status.found_count, watching=status.watching_count)
            )
        else:
            self.lbl_found.configure(text=tr("ui.found_none"))
        self._render_meta(status)

    def _render_meta(self, status: Status) -> None:
        bits = [tr("ui.last_check", time=clock(status.ts))]
        if status.rate_mbps > 0:
            bits.append(tr("ui.net", mbps=status.rate_mbps))
        if status.io_bps > 0:
            bits.append(tr("ui.disk", speed=fmt_speed(status.io_bps)))
        auto = int(self.cfg.get("auto_refresh_seconds") or 0)
        if auto > 0:
            bits.append(tr("ui.auto_refresh", seconds=auto))
        bits.append(f"Steam {'✓' if status.steam_running else '✗'}")
        bits.append(f"Epic {'✓' if status.epic_running else '✗'}")
        self.lbl_meta.configure(text="  ·  ".join(bits))

    def _render_apps(self, apps: list[dict]) -> None:
        keys = [a["key"] for a in apps]
        if keys != list(self.rows.keys()):
            for child in self.apps_inner.winfo_children():
                child.destroy()
            self.rows.clear()
            self.lbl_empty = None
            for app in apps:
                self.rows[app["key"]] = self._create_row(app)
            if not apps:
                self.lbl_empty = tk.Label(
                    self.apps_inner, text=tr("ui.empty"), bg=BG, fg=MUTED, font=FONT, justify="left", anchor="w"
                )
                self.lbl_empty.pack(fill="x", pady=8)

        for app in apps:
            row = self.rows.get(app["key"])
            if row:
                self._update_row(row, app)

    def _create_row(self, app: dict) -> dict:
        frame = tk.Frame(self.apps_inner, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="x", pady=(0, 6))
        inner = tk.Frame(frame, bg=CARD)
        inner.pack(fill="x", padx=12, pady=8)

        top = tk.Frame(inner, bg=CARD)
        top.pack(fill="x")

        key = app["key"]
        var = tk.BooleanVar(value=bool(app.get("watched")))
        watch = tk.Checkbutton(
            top,
            text="",
            variable=var,
            command=lambda k=key, v=var: self.detector.set_watched(k, bool(v.get())),
            bg=CARD,
            fg=FG,
            activebackground=CARD,
            activeforeground=FG,
            selectcolor=CARD2,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        watch.pack(side="left", padx=(0, 6))

        source = tk.Label(
            top,
            text=app["source"].upper(),
            bg=CARD2,
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=1,
        )
        source.pack(side="left", padx=(0, 8))

        name = tk.Label(top, text=app["name"], bg=CARD, fg=FG, font=FONT_B, anchor="w")
        name.pack(side="left", fill="x", expand=True)

        value = tk.Label(top, text="", bg=CARD, fg=FG, font=FONT_SM, anchor="e")
        value.pack(side="right")

        bar = ttk.Progressbar(inner, style="Bar.Horizontal.TProgressbar", maximum=100, value=0)
        bar.pack(fill="x", pady=(6, 3))

        sub = tk.Label(inner, text="", bg=CARD, fg=MUTED, font=FONT_SM, anchor="w")
        sub.pack(fill="x")

        return {"frame": frame, "name": name, "value": value, "bar": bar, "sub": sub, "var": var, "watch": watch}

    def _update_row(self, row: dict, app: dict) -> None:
        watched = bool(app.get("watched"))
        if row["var"].get() != watched:
            row["var"].set(watched)
        row["name"].configure(text=app["name"], fg=FG if watched else MUTED)
        if app.get("complete"):
            row["value"].configure(text=tr("ui.row_completed"), fg=GREEN)
            row["bar"].configure(style="BarDone.Horizontal.TProgressbar", value=100)
            size = app.get("size_on_disk") or app.get("total")
            if size:
                row["sub"].configure(text=tr("row.on_disk", size=fmt_bytes(size)), fg=GREEN)
            else:
                row["sub"].configure(text=tr("ui.row_installed"), fg=GREEN)
            return

        row["value"].configure(text=pct(app.get("progress")), fg=FG)
        row["bar"].configure(style="Bar.Horizontal.TProgressbar", value=(app.get("progress") or 0) * 100)

        parts = []
        if app.get("total"):
            parts.append(f"{fmt_bytes(app['downloaded'])} / {fmt_bytes(app['total'])}")
        if app.get("size_on_disk"):
            parts.append(tr("row.on_disk", size=fmt_bytes(app["size_on_disk"])))
        if app.get("rate_bps"):
            parts.append(fmt_speed(app["rate_bps"]))
        if app.get("eta"):
            parts.append(f"~{fmt_duration(app['eta'])}")
        if app.get("note_key"):
            parts.append(tr(app["note_key"]))
        row["sub"].configure(text="  ·  ".join(parts) or tr("ui.row_downloading"), fg=MUTED)

    # ------------------------------------------------------------------ log text
    def _append_log_entry(self, entry: tuple[float, str, str, dict]) -> None:
        ts, level, key, params = entry
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", f"[{clock(ts)}] ", "time")
        self.txt_log.insert("end", tr(key, **params) + "\n", level)
        self.txt_log.configure(state="disabled")
        self.txt_log.see("end")
        if len(self.log_entries) > 800:
            self._render_log()

    def _render_log(self) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        entries = self.log_entries[-600:]
        for ts, level, key, params in entries:
            self.txt_log.insert("end", f"[{clock(ts)}] ", "time")
            self.txt_log.insert("end", tr(key, **params) + "\n", level)
        self.txt_log.configure(state="disabled")
        self.txt_log.see("end")

    # ------------------------------------------------------------------ run
    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    AppUI().run()
