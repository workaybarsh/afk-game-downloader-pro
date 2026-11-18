"""Render the wizard pages to PNG files for a visual check."""

from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from PIL import ImageGrab  # noqa: E402

from tools.capture_window import capture  # noqa: E402


def shoot_setup(pages: list[int], prefix: str) -> None:
    from setup_tool.wizard import SetupWizard

    wizard = SetupWizard()
    wizard.root.deiconify()
    wizard.root.update()
    for page in pages:
        wizard._show_page(page)
        wizard.root.update()
        time.sleep(0.4)
        out = Path.home() / "AppData" / "Local" / "Temp" / f"{prefix}_{page}.png"
        capture(wizard.root.title(), str(out))
        print(out)
    wizard.root.destroy()


def shoot_uninstall(prefix: str) -> None:
    from setup_tool.uninstall_ui import UninstallWizard

    wizard = UninstallWizard(Path(r"C:\Users\Example\AppData\Local\Programs\AFK Game Downloader Pro"))
    wizard.root.deiconify()
    wizard.root.update()
    time.sleep(0.4)
    out = Path.home() / "AppData" / "Local" / "Temp" / f"{prefix}.png"
    capture(wizard.root.title(), str(out))
    print(out)
    wizard.root.destroy()


if __name__ == "__main__":
    shoot_setup([1, 2, 4], "wiz")
    shoot_uninstall("uninst")
