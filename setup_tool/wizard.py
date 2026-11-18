"""Setup wizard for AFK Game Downloader Pro.

Flow (same shape as the reference installer): welcome -> destination -> tasks ->
ready -> installing -> finish. Installs per-user, no administrator rights.
"""

from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

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
FONT_H1 = ("Segoe UI Semibold", 16)
FONT_H2 = ("Segoe UI Semibold", 12)

TOTAL_STEPS = 6


def _detect_language() -> str:
    try:
        raw = json.loads((Path(os.environ.get("APPDATA", "")) / "AFKGameDownloaderPro" / "config.json").read_text("utf-8"))
        if isinstance(raw, dict) and raw.get("language") in i18n.STRINGS:
            return str(raw["language"])
    except (OSError, ValueError):
        pass
    return i18n.DEFAULT_LANG


class SetupWizard:
    def __init__(self) -> None:
        i18n.set_lang(_detect_language())

        self.root = tk.Tk()
        self.root.configure(bg=BG)
        self.root.title(tr("setup.title"))
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._cancel)

        self.install_dir = tk.StringVar(value=str(ops.default_install_dir()))
        self.opt_desktop = tk.BooleanVar(value=True)
        self.opt_startmenu = tk.BooleanVar(value=True)
        self.opt_launch = tk.BooleanVar(value=True)
        self.accepted_license = tk.BooleanVar(value=False)
        self.page = 0
        self.busy = False
        self.language = i18n.get_lang()
        self._icon_small: tk.PhotoImage | None = None
        self._icon_large: tk.PhotoImage | None = None

        self._geometry()
        self._load_icons()
        self._set_window_icon()
        self._build_shell()
        self._show_page(0)

    # ------------------------------------------------------------------ chrome
    def _geometry(self) -> None:
        width, height = 660, 520
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _load_icons(self) -> None:
        """Load the artwork at its native sizes (no nearest-neighbour scaling)."""
        large = ops.asset_path("icon_128.png") or ops.asset_path("app_preview.png")
        small = ops.asset_path("icon_32.png") or large
        try:
            if large:
                self._icon_large = tk.PhotoImage(file=str(large))
            if small:
                self._icon_small = tk.PhotoImage(file=str(small))
        except tk.TclError:
            pass

    def _set_window_icon(self) -> None:
        ico = ops.asset_path("app.ico")
        try:
            if ico:
                self.root.iconbitmap(default=str(ico))
        except tk.TclError:
            pass
        try:
            images = [img for img in (self._icon_large, self._icon_small) if img is not None]
            if images:
                self.root.iconphoto(True, *images)
        except tk.TclError:
            pass

    def _build_shell(self) -> None:
        header = tk.Frame(self.root, bg=CARD, highlightthickness=0)
        header.pack(fill="x")
        inner = tk.Frame(header, bg=CARD)
        inner.pack(fill="x", padx=16, pady=10)

        if self._icon_small:
            tk.Label(inner, image=self._icon_small, bg=CARD).pack(side="left", padx=(0, 10))
        self.lbl_app = tk.Label(inner, text=tr("setup.title"), bg=CARD, fg=FG, font=FONT_H2)
        self.lbl_app.pack(side="left")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=22, pady=16)

        footer = tk.Frame(self.root, bg=CARD)
        footer.pack(fill="x", side="bottom")
        tk.Frame(footer, bg=BORDER, height=1).pack(fill="x", side="top")
        nav = tk.Frame(footer, bg=CARD)
        nav.pack(fill="x", padx=16, pady=10)

        self.lbl_step = tk.Label(nav, text="", bg=CARD, fg=MUTED, font=FONT_SM)
        self.lbl_step.pack(side="left")

        self.btn_cancel = self._button(nav, tr("setup.btn_cancel"), self._cancel, CARD2, MUTED)
        self.btn_cancel.pack(side="right")
        self.btn_next = self._button(nav, tr("setup.btn_next"), self._next, ACCENT, "white")
        self.btn_next.pack(side="right", padx=(0, 8))
        self.btn_back = self._button(nav, tr("setup.btn_back"), self._back, CARD2, FG)
        self.btn_back.pack(side="right", padx=(0, 8))

    def _button(self, parent, text: str, command, bg: str, fg: str) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=BORDER,
            activeforeground=fg,
            relief="flat",
            font=FONT_B,
            padx=16,
            pady=4,
            cursor="hand2",
        )

    def _check(self, parent, text: str, var: tk.BooleanVar) -> tk.Checkbutton:
        return tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            bg=BG,
            fg=FG,
            activebackground=BG,
            activeforeground=FG,
            selectcolor=CARD2,
            font=FONT,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )

    # ------------------------------------------------------------------ pages
    def _clear(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    def _heading(self, title: str, description: str) -> None:
        tk.Label(self.body, text=title, bg=BG, fg=FG, font=FONT_H1, anchor="w", justify="left", wraplength=600).pack(
            fill="x"
        )
        tk.Label(
            self.body,
            text=description,
            bg=BG,
            fg=MUTED,
            font=FONT,
            anchor="w",
            justify="left",
            wraplength=600,
        ).pack(fill="x", pady=(8, 14))

    def _show_page(self, page: int) -> None:
        self.page = page
        self._clear()

        if page == 0:
            self._welcome_page()
        elif page == 1:
            self._language_page()
        elif page == 2:
            self._license_page()
        elif page == 3:
            self._destination_page()
        elif page == 4:
            self._tasks_page()
        elif page == 5:
            self._ready_page()
        elif page == 6:
            self._installing_page()
        elif page == 7:
            self._finish_page()

        self._update_nav()

    def _update_nav(self) -> None:
        if self.page == 7:
            self.lbl_step.configure(text="")
            self.btn_back.configure(state="disabled", fg=MUTED)
            self.btn_next.configure(text=tr("setup.btn_finish"), state="normal")
            self.btn_cancel.configure(state="disabled", fg=MUTED)
            return
        if self.page == 6:
            self.lbl_step.configure(text="")
            self.btn_back.configure(state="disabled", fg=MUTED)
            self.btn_next.configure(state="disabled")
            self.btn_cancel.configure(state="disabled", fg=MUTED)
            return

        self.lbl_step.configure(text=tr("setup.step", current=self.page + 1, total=TOTAL_STEPS))
        self.btn_back.configure(state="normal" if self.page > 0 else "disabled", fg=FG if self.page > 0 else MUTED)
        self.btn_next.configure(text=tr("setup.btn_install") if self.page == 5 else tr("setup.btn_next"), state="normal")
        self.btn_cancel.configure(state="normal", fg=MUTED)

    def _welcome_page(self) -> None:
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="both", expand=True)
        if self._icon_large:
            tk.Label(row, image=self._icon_large, bg=BG).pack(side="left", anchor="n", padx=(0, 18))
        text = tk.Frame(row, bg=BG)
        text.pack(side="left", fill="both", expand=True)
        tk.Label(
            text,
            text=tr("setup.welcome_title"),
            bg=BG,
            fg=FG,
            font=FONT_H1,
            anchor="w",
            justify="left",
            wraplength=400,
        ).pack(fill="x")
        tk.Label(
            text,
            text=tr("setup.welcome_body"),
            bg=BG,
            fg=MUTED,
            font=FONT,
            anchor="w",
            justify="left",
            wraplength=400,
        ).pack(fill="x", pady=(12, 0))

    def _language_page(self) -> None:
        """Pick the installation language from a short list."""
        tk.Label(
            self.body,
            text=tr("setup.lang_title"),
            bg=BG,
            fg=FG,
            font=FONT_H1,
            anchor="w",
        ).pack(fill="x", pady=(10, 0))
        tk.Label(
            self.body,
            text=tr("setup.lang_body"),
            bg=BG,
            fg=MUTED,
            font=FONT,
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", pady=(6, 18))

        box = tk.Frame(self.body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        box.pack(fill="x")
        self.lang_list = tk.Listbox(
            box,
            height=2,
            bg=CARD,
            fg=FG,
            selectbackground=ACCENT,
            selectforeground="white",
            bd=0,
            highlightthickness=0,
            activestyle="none",
            font=("Segoe UI", 12),
            cursor="hand2",
        )
        for label in i18n.LANGUAGES.values():
            self.lang_list.insert("end", f"   {label}")
        self.lang_list.pack(fill="x", padx=1, pady=1, ipady=6)
        codes = list(i18n.LANGUAGES.keys())
        index = codes.index(self.language) if self.language in codes else 0
        self.lang_list.selection_set(index)
        self.lang_list.bind("<<ListboxSelect>>", self._on_language_select)

        tk.Label(
            self.body,
            text=tr("setup.lang_hint"),
            bg=BG,
            fg=MUTED,
            font=FONT_SM,
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", pady=(12, 0))

    def _license_page(self) -> None:
        self._heading(tr("setup.license_title"), tr("setup.license_body"))
        box = tk.Frame(self.body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        box.pack(fill="both", expand=True)
        text = tk.Text(
            box,
            bg=CARD,
            fg=MUTED,
            relief="flat",
            wrap="word",
            font=("Consolas", 8),
            padx=10,
            pady=8,
            height=12,
        )
        text.insert("1.0", ops.license_text())
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)
        self._check(self.body, tr("setup.license_accept"), self.accepted_license).pack(anchor="w", pady=(10, 0))

    def _destination_page(self) -> None:
        self._heading(tr("setup.dest_title"), tr("setup.dest_body"))
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x")
        entry = tk.Entry(
            row,
            textvariable=self.install_dir,
            bg=CARD2,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            font=FONT,
        )
        entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))
        self._button(row, tr("setup.browse"), self._browse, CARD2, FG).pack(side="left")

        note = tk.Label(self.body, text="", bg=BG, fg=MUTED, font=FONT_SM, anchor="w", justify="left", wraplength=600)
        note.pack(fill="x", pady=(12, 0))
        self._dest_note = note
        self.install_dir.trace_add("write", lambda *_: self._update_dest_note())
        self._update_dest_note()

    def _update_dest_note(self) -> None:
        if not hasattr(self, "_dest_note"):
            return
        try:
            target = Path(self.install_dir.get())
        except (OSError, ValueError):
            return
        if (target / ops.APP_EXE).is_file():
            self._dest_note.configure(text=tr("setup.exists"), fg=GREEN)
        else:
            self._dest_note.configure(text="", fg=MUTED)

    def _browse(self) -> None:
        current = Path(self.install_dir.get() or ops.default_install_dir())
        initial = current if current.is_dir() else current.parent
        selected = filedialog.askdirectory(title=tr("setup.dest_title"), initialdir=str(initial))
        if selected:
            self.install_dir.set(str(Path(selected) / ops.APP_NAME))

    def _tasks_page(self) -> None:
        self._heading(tr("setup.tasks_title"), tr("setup.tasks_body"))
        self._check(self.body, tr("setup.task_desktop"), self.opt_desktop).pack(anchor="w", pady=(2, 0))
        self._check(self.body, tr("setup.task_startmenu"), self.opt_startmenu).pack(anchor="w", pady=(6, 0))

    def _tasks_summary(self) -> str:
        items = []
        if self.opt_desktop.get():
            items.append(tr("setup.task_desktop"))
        if self.opt_startmenu.get():
            items.append(tr("setup.task_startmenu"))
        return "\n".join(items) if items else tr("setup.none")

    def _ready_page(self) -> None:
        self._heading(tr("setup.ready_title"), tr("setup.ready_body"))
        card = tk.Frame(self.body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="both", expand=True)
        tk.Label(
            card,
            text=tr("setup.summary_dest"),
            bg=CARD,
            fg=MUTED,
            font=FONT_SM,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 2))
        tk.Label(
            card,
            text=self.install_dir.get(),
            bg=CARD,
            fg=FG,
            font=FONT,
            anchor="w",
            justify="left",
            wraplength=580,
        ).pack(fill="x", padx=14)
        tk.Label(
            card,
            text=tr("setup.summary_tasks"),
            bg=CARD,
            fg=MUTED,
            font=FONT_SM,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(14, 2))
        tk.Label(
            card,
            text=self._tasks_summary(),
            bg=CARD,
            fg=FG,
            font=FONT,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=14, pady=(0, 12))

    def _installing_page(self) -> None:
        self._heading(tr("setup.installing_title"), tr("setup.installing_body"))
        self.status = tk.StringVar(value=tr("setup.msg_prepare"))
        tk.Label(self.body, textvariable=self.status, bg=BG, fg=MUTED, font=FONT, anchor="w").pack(fill="x")
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Setup.Horizontal.TProgressbar",
            troughcolor=CARD2,
            background=ACCENT,
            bordercolor=CARD2,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=10,
        )
        self.progress = ttk.Progressbar(self.body, style="Setup.Horizontal.TProgressbar", maximum=100, value=0)
        self.progress.pack(fill="x", pady=(14, 0))

    def _finish_page(self) -> None:
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="both", expand=True)
        if self._icon_large:
            tk.Label(row, image=self._icon_large, bg=BG).pack(side="left", anchor="n", padx=(0, 18))
        text = tk.Frame(row, bg=BG)
        text.pack(side="left", fill="both", expand=True)
        tk.Label(
            text,
            text=tr("setup.finish_title"),
            bg=BG,
            fg=GREEN,
            font=FONT_H1,
            anchor="w",
            justify="left",
            wraplength=400,
        ).pack(fill="x")
        tk.Label(
            text,
            text=tr("setup.finish_body"),
            bg=BG,
            fg=MUTED,
            font=FONT,
            anchor="w",
            justify="left",
            wraplength=400,
        ).pack(fill="x", pady=(12, 0))
        self._check(text, tr("setup.launch"), self.opt_launch).pack(anchor="w", pady=(18, 0))

    # ------------------------------------------------------------------ actions
    def _next(self) -> None:
        if self.page == 0:
            self._show_page(1)
            return
        if self.page == 1:
            self._show_page(2)
            return
        if self.page == 2:
            if not self.accepted_license.get():
                messagebox.showwarning(tr("setup.license_title"), tr("setup.license_required"), parent=self.root)
                return
            self._show_page(3)
            return
        if self.page == 3:
            target = Path(self.install_dir.get().strip())
            ok, reason = ops.validate_target(target)
            if not ok:
                messagebox.showerror(tr("setup.err_title"), tr(reason), parent=self.root)
                return
            if not target.name:
                messagebox.showerror(tr("setup.err_title"), tr("setup.err_system"), parent=self.root)
                return
            self._show_page(4)
            return
        if self.page == 4:
            self._show_page(5)
            return
        if self.page == 5:
            self._start_install()
            return
        if self.page == 7:
            if self.opt_launch.get():
                try:
                    ops.launch(Path(self.install_dir.get()))
                except OSError as exc:
                    messagebox.showwarning(tr("setup.err_title"), tr("setup.launch_failed", error=exc), parent=self.root)
            self.root.destroy()

    def _back(self) -> None:
        if self.page > 0 and not self.busy:
            self._show_page(self.page - 1)

    def _cancel(self) -> None:
        if self.busy:
            return
        if self.page == 0 or messagebox.askyesno(tr("setup.cancel_title"), tr("setup.cancel_body"), parent=self.root):
            self.root.destroy()

    def _set_language(self, code: str) -> None:
        """Apply and remember the language chosen on the language page."""
        self.language = i18n.set_lang(code)
        ops.write_language(self.language)
        self.root.title(tr("setup.title"))
        self.lbl_app.configure(text=tr("setup.title"))
        self.btn_back.configure(text=tr("setup.btn_back"))
        self.btn_cancel.configure(text=tr("setup.btn_cancel"))
        self.btn_next.configure(
            text=tr("setup.btn_install") if self.page == 5 else tr("setup.btn_next")
        )
        self._show_page(self.page)

    def _on_language_select(self, _event=None) -> None:
        if self.busy:
            return
        selection = self.lang_list.curselection()
        if not selection:
            return
        codes = list(i18n.LANGUAGES.keys())
        index = selection[0]
        if 0 <= index < len(codes):
            self._set_language(codes[index])

    def _start_install(self) -> None:
        target = Path(self.install_dir.get().strip())
        ok, reason = ops.validate_target(target)
        if not ok:
            messagebox.showerror(tr("setup.err_title"), tr(reason), parent=self.root)
            return

        self.busy = True
        self._show_page(6)
        options = {
            "desktop": bool(self.opt_desktop.get()),
            "start_menu": bool(self.opt_startmenu.get()),
        }
        threading.Thread(target=self._run_install, args=(target, options), daemon=True).start()

    def _progress(self, percent: int, key: str) -> None:
        def apply() -> None:
            try:
                self.progress.configure(value=percent)
                self.status.set(tr(key))
            except tk.TclError:
                pass

        self.root.after(0, apply)

    def _run_install(self, target: Path, options: dict) -> None:
        try:
            ops.install(target, options, self._progress)
            ops.write_language(self.language)
        except OSError as exc:
            self.root.after(0, lambda exc=exc: self._install_failed(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda exc=exc: self._install_failed(exc))
            return
        self.root.after(0, self._install_done)

    def _install_done(self) -> None:
        self.busy = False
        self._show_page(7)

    def _install_failed(self, exc: Exception) -> None:
        self.busy = False
        message = str(exc)
        text = tr(message) if message.startswith("setup.") else message
        self._show_page(5)
        messagebox.showerror(tr("setup.err_title"), text, parent=self.root)

    # ------------------------------------------------------------------ run
    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    SetupWizard().run()
    return 0
