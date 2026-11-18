"""AFK Game Downloader Pro - setup wizard entry point.

Hidden switches (used by the build tests):
    --check              verify the bundled payload can be located
    --silent [--target D]  install with default options and exit
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

RESULT = Path(os.environ.get("TEMP", ".")) / "afkdl_setup_result.txt"


def _self_check() -> int:
    try:
        from setup_tool import ops

        payload = ops.payload_exe()
        uninstaller = ops.uninstaller_payload()
        RESULT.write_text(
            f"OK {payload} {payload.stat().st_size} | {uninstaller}",
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        RESULT.write_text(f"FAIL {exc}", encoding="utf-8")
        return 1
    return 0


def _silent_install(argv: list[str]) -> int:
    from setup_tool import ops

    target = ops.default_install_dir()
    if "--target" in argv:
        target = Path(argv[argv.index("--target") + 1])
    try:
        ops.install(
            target,
            {"desktop": True, "start_menu": True},
        )
    except Exception as exc:  # noqa: BLE001
        RESULT.write_text(f"FAIL {exc}", encoding="utf-8")
        return 1
    RESULT.write_text(f"OK {target}", encoding="utf-8")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return _self_check()
    if "--silent" in sys.argv:
        return _silent_install(sys.argv)

    from setup_tool.wizard import main as wizard_main

    return wizard_main()


if __name__ == "__main__":
    sys.exit(main())
