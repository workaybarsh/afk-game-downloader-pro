"""Uninstall wizard: removes the app, shortcuts, registry entries and settings."""

from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from afkdl import i18n
from afkdl.i18n import tr

from . import ops

BG = "#0d1117"
CARD = "#161b22"
CARD2 = "#21262d"
BORDER = "#30363d"
FG = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#2f81f7"
GREEN = "#3fb950"
RED = "#f85149"

FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI Semibold", 10)
FONT_SM = ("Segoe UI", 9)
FONT_H1 = ("Segoe UI Semibold", 15)
FONT_H2 = ("Segoe UI Semibold", 12)


def _detect_language() -> str:
    try:
        path = Path(os.environ.get("APPDATA", "")) / "AFKGameDownloaderPro" / "config.json"
        raw = json.loads(path.read_text("utf-8"))
        if isinstance(raw, dict) and raw.get("language") in i18n.STRINGS:
            return str(raw["language"])
    except (OSError, ValueError):
        pass
    return i18n.DEFAULT_LANG


class UninstallWizard:
    def __init__(self, target: Path) -> None:
        i18n.set_lang(_detect_language())
        self.target = target
        self.busy = False
        self.done = False

        self.root = tk.Tk()
        self.root.configure(bg=BG)
        self.root.title(tr("uninstall.title"))
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        width, height = 600, 430
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self._icon_small = None
        self._load_icons()
        self._build()
        self._show_confirm()

    # ------------------------------------------------------------------ chrome
    def _load_icons(self) -> None:
        path = ops.asset_path("icon_32.png") or ops.asset_path("app_preview.png")
        try:
            if path:
                self._icon_small = tk.PhotoImage(file=str(path))
        except tk.TclError:
            self._icon_small = None
        ico = ops.asset_path("app.ico")
        try:
            if ico:
                self.root.iconbitmap(default=str(ico))
        except tk.TclError:
            pass
        try:
            if self._icon_small:
                self.root.iconphoto(True, self._icon_small)
        except tk.TclError:
            pass

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=CARD)
        header.pack(fill="x")
        inner = tk.Frame(header, bg=CARD)
        inner.pack(fill="x", padx=16, pady=10)
        if self._icon_small:
            tk.Label(inner, image=self._icon_small, bg=CARD).pack(side="left", padx=(0, 10))
        tk.Label(inner, text=tr("uninstall.title"), bg=CARD, fg=FG, font=FONT_H2).pack(side="left")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=22, pady=14)

        footer = tk.Frame(self.root, bg=CARD)
        footer.pack(fill="x", side="bottom")
        tk.Frame(footer, bg=BORDER, height=1).pack(fill="x", side="top")
        nav = tk.Frame(footer, bg=CARD)
        nav.pack(fill="x", padx=16, pady=10)

        self.btn_cancel = tk.Button(
            nav,
            text=tr("uninstall.cancel"),
            command=self._close,
            bg=CARD2,
            fg=FG,
            activebackground=BORDER,
            activeforeground=FG,
            relief="flat",
            font=FONT_B,
            padx=16,
            pady=4,
            cursor="hand2",
        )
        self.btn_cancel.pack(side="right")

        self.btn_run = tk.Button(
            nav,
            text=tr("uninstall.btn"),
            command=self._start,
            bg="#7f1d1d",
            fg="#ffb4b4",
            activebackground=BORDER,
            activeforeground="#ffb4b4",
            relief="flat",
            font=FONT_B,
            padx=16,
            pady=4,
            cursor="hand2",
        )
        self.btn_run.pack(side="right", padx=(0, 8))

    def _clear(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    # ------------------------------------------------------------------ pages
    def _show_confirm(self) -> None:
        self._clear()
        tk.Label(
            self.body,
            text=tr("uninstall.heading"),
            bg=BG,
            fg=FG,
            font=FONT_H1,
            anchor="w",
            justify="left",
            wraplength=540,
        ).pack(fill="x")
        tk.Label(
            self.body,
            text=str(self.target),
            bg=BG,
            fg=MUTED,
            font=FONT_SM,
            anchor="w",
            justify="left",
            wraplength=540,
        ).pack(fill="x", pady=(4, 12))

        card = tk.Frame(self.body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x")
        for key in ("uninstall.item_app", "uninstall.item_shortcuts", "uninstall.item_settings"):
            tk.Label(card, text="•  " + tr(key), bg=CARD, fg=FG, font=FONT, anchor="w").pack(
                fill="x", padx=14, pady=(8, 0)
            )

    def _show_progress(self) -> None:
        self._clear()
        tk.Label(self.body, text=tr("uninstall.progress"), bg=BG, fg=FG, font=FONT_H1, anchor="w").pack(fill="x")
        self.status = tk.StringVar(value=tr("uninstall.msg_stop"))
        tk.Label(self.body, textvariable=self.status, bg=BG, fg=MUTED, font=FONT, anchor="w").pack(fill="x", pady=(10, 8))

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Uninst.Horizontal.TProgressbar",
            troughcolor=CARD2,
            background=ACCENT,
            bordercolor=CARD2,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=10,
        )
        self.bar = ttk.Progressbar(self.body, style="Uninst.Horizontal.TProgressbar", maximum=100, value=0)
        self.bar.pack(fill="x")

    def _show_done(self) -> None:
        self._clear()
        tk.Label(self.body, text=tr("uninstall.done_title"), bg=BG, fg=GREEN, font=FONT_H1, anchor="w").pack(fill="x")
        tk.Label(
            self.body,
            text=tr("uninstall.done_body"),
            bg=BG,
            fg=MUTED,
            font=FONT,
            anchor="w",
            justify="left",
            wraplength=540,
        ).pack(fill="x", pady=(10, 0))
        self.btn_run.configure(
            text=tr("uninstall.close"),
            state="normal",
            bg=ACCENT,
            fg="white",
            command=self._close,
        )
        self.btn_cancel.pack_forget()

    # ------------------------------------------------------------------ actions
    def _start(self) -> None:
        if self.busy:
            return
        self.busy = True
        self.btn_run.configure(state="disabled")
        self.btn_cancel.configure(state="disabled")
        self._show_progress()
        threading.Thread(target=self._run, daemon=True).start()

    def _progress(self, percent: int, key: str) -> None:
        def apply() -> None:
            try:
                self.bar.configure(value=percent)
                self.status.set(tr(key))
            except tk.TclError:
                pass

        self.root.after(0, apply)

    def _run(self) -> None:
        try:
            ops.uninstall_all(self.target, True, self._progress)
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda exc=exc: self._failed(exc))
            return
        self.root.after(0, self._show_done)

    def _failed(self, exc: Exception) -> None:
        self.busy = False
        self.btn_run.configure(state="normal")
        self.btn_cancel.configure(state="normal")
        self.status.set(str(exc))

    def _close(self) -> None:
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else [])
    target = ops.installed_dir()
    if "--target" in argv:
        target = Path(argv[argv.index("--target") + 1])
    if "--quiet" in argv:
        remove_settings = "--keep-settings" not in argv
        ops.uninstall_all(target, remove_settings)
        return 0
    UninstallWizard(target).run()
    return 0
