"""AFK Game Downloader Pro - uninstall wizard entry point."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def main() -> int:
    from setup_tool.uninstall_ui import main as uninstall_main

    return uninstall_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
