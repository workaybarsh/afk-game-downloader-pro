"""Repo hygiene check: no localized text outside i18n.py."""

from __future__ import annotations

import pathlib
import re

TR_CHARS = re.compile(r"[ıİşŞğĞçÇöÖüÜ]")
ALLOWED = {"i18n.py", "test_ui.py", "readme.md", "check_language.py", "test_logic.py"}


def main() -> int:
    bad: list[str] = []
    for path in pathlib.Path(".").rglob("*"):
        if path.is_dir() or path.suffix.lower() not in {".py", ".md", ".bat", ".vbs"}:
            continue
        if path.name.lower() in ALLOWED:
            continue
        if "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text("utf-8")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", '"""', "'")):
                continue
            if TR_CHARS.search(line):
                bad.append(f"{path}:{number}: {stripped[:100]}")

    if bad:
        print("Non-English text found outside i18n.py:")
        print("\n".join(bad))
        return 1
    print("OK: no localized text outside afkdl/i18n.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
