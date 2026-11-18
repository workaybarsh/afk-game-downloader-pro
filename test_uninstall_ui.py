"""Guards the uninstaller's final page: the Close button must actually work.

Run:  python test_uninstall_ui.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from afkdl import i18n  # noqa: E402


def main() -> int:
    from setup_tool.uninstall_ui import UninstallWizard

    wizard = UninstallWizard(Path(r"C:\Fake\AFK Game Downloader Pro"))
    wizard.root.withdraw()
    wizard.root.update()

    wizard._show_done()
    wizard.root.update()

    state = str(wizard.btn_run.cget("state"))
    assert state == "normal", f"Close button is '{state}' - it must be clickable"
    print(f"[OK] Close button is enabled ({wizard.btn_run.cget('text')})")

    assert str(wizard.btn_cancel.winfo_manager()) == "", "cancel button should be hidden on the done page"
    print("[OK] Cancel button hidden on the done page")

    wizard._close()
    print("[OK] Close destroys the window")

    i18n.set_lang("tr")
    wizard2 = UninstallWizard(Path(r"C:\Fake\AFK Game Downloader Pro"))
    wizard2.root.withdraw()
    i18n.set_lang("tr")  # the wizard restores the app's saved language on start
    wizard2._show_done()
    wizard2.root.update()
    assert wizard2.btn_run.cget("text") == "Kapat", wizard2.btn_run.cget("text")
    print("[OK] Turkish label")
    wizard2._close()

    print("\n UNINSTALLER UI TEST PASSED\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
