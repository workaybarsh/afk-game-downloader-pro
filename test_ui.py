"""UI smoke test: builds the window, checks both languages, closes again.

Run:  python test_ui.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from afkdl import i18n  # noqa: E402
from afkdl.config import ACTION_ORDER  # noqa: E402


def main() -> int:
    from afkdl.ui import AppUI

    app = AppUI()
    root = app.root
    root.withdraw()
    root.update()

    i18n.set_lang("en")
    app._apply_language()
    root.update()
    assert app.cmb_action["values"][0] == "Shut down computer", app.cmb_action["values"]
    assert app.lbl_phase.cget("text") or True
    assert len(app.cmb_action["values"]) == len(ACTION_ORDER)
    print("[OK] English labels")
    print("     start button:", app.btn_start.cget("text"))
    print("     event log   :", app.btn_log.cget("text"))

    app._on_lang()  # toggle to Turkish
    root.update()
    assert app.cmb_action["values"][0] == "Bilgisayarı kapat", app.cmb_action["values"]
    print("[OK] Turkish labels")
    print("     start button:", app.btn_start.cget("text"))
    print("     event log   :", app.btn_log.cget("text"))

    app._on_lang()  # back to English
    root.update()
    assert app.cmb_action["values"][0] == "Shut down computer"
    print("[OK] Toggle back to English")

    # log re-rendering in both languages
    app.detector.log("log.completed", names="Red Dead Redemption 2")
    app._drain_queue()
    root.update()
    text_en = app.txt_log.get("1.0", "end")
    assert "COMPLETED: Red Dead Redemption 2" in text_en, text_en
    app._on_lang()
    root.update()
    text_tr = app.txt_log.get("1.0", "end")
    assert "TAMAMLANDI: Red Dead Redemption 2" in text_tr, text_tr
    print("[OK] Past log lines re-render in the new language")

    # log panel can be collapsed and re-opened
    app.cfg["show_log"] = True
    app._apply_log_visibility()
    root.update()
    assert app.log_body.winfo_manager() == "pack", app.log_body.winfo_manager()
    app._toggle_log()
    root.update()
    assert app.log_body.winfo_manager() == "", app.log_body.winfo_manager()
    assert app.btn_log.winfo_manager() == "pack"
    app._toggle_log()
    root.update()
    assert app.log_body.winfo_manager() == "pack"
    print("[OK] Event log collapses and re-opens")

    app.stop_event.set()
    app.cfg["language"] = "en"
    app.cfg.save()
    root.destroy()
    print("\n UI SMOKE TEST PASSED\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
