"""Run the whole test suite and print a summary.

    python test_all.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable

SUITE = [
    ("decision engine", [PY, "test_logic.py"]),
    ("epic detection", [PY, "test_epic.py"]),
    ("ui + language", [PY, "test_ui.py"]),
    ("installer install/uninstall", [PY, "test_installer.py"]),
    ("uninstaller ui", [PY, "test_uninstall_ui.py"]),
    ("localization hygiene", [PY, "check_language.py"]),
]


def run(label: str, command: list[str]) -> tuple[str, bool, float, str]:
    start = time.time()
    proc = subprocess.run(
        command,
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - start
    ok = proc.returncode == 0
    output = (proc.stdout or "") + (proc.stderr or "")
    return label, ok, elapsed, output


def check_binaries() -> list[tuple[str, bool, float, str]]:
    results = []
    for name in ("AFK Game Downloader Pro.exe", "AFK Game Downloader Pro Setup.exe"):
        path = HERE / "dist" / name
        ok = path.is_file() and path.stat().st_size > 1_000_000
        detail = f"{path.stat().st_size / 1e6:.1f} MB" if path.is_file() else "missing"
        results.append((name, ok, 0.0, detail))

    icon = subprocess.run(
        [PY, "tools/check_icon.py", "dist/AFK Game Downloader Pro.exe", "dist/AFK Game Downloader Pro Setup.exe"],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    results.append(("icons in both executables", icon.returncode == 0, 0.0, ""))
    return results


def main() -> int:
    print("=" * 68)
    print(" AFK Game Downloader Pro - FULL TEST RUN")
    print("=" * 68)

    results: list[tuple[str, bool, float, str]] = []
    outputs: dict[str, str] = {}

    for label, command in SUITE:
        print(f"\n>>> {label} ...", flush=True)
        name, ok, elapsed, output = run(label, command)
        results.append((name, ok, elapsed, ""))
        outputs[name] = output
        tail = [line for line in output.strip().splitlines() if line.strip()][-1:] or [""]
        print(f"    {'PASS' if ok else 'FAIL'}  ({elapsed:.1f}s)  {tail[0][:80]}")

    print("\n>>> binaries ...", flush=True)
    for item in check_binaries():
        results.append(item)
        print(f"    {'PASS' if item[1] else 'FAIL'}  {item[0]}  {item[3]}")

    print("\n" + "=" * 68)
    print(" SUMMARY")
    print("=" * 68)
    failures = 0
    for name, ok, elapsed, detail in results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        timing = f"{elapsed:5.1f}s" if elapsed else "      "
        print(f"  [{status}] {timing}  {name} {detail}")
    print("=" * 68)

    if failures:
        print(f"\n {failures} test group(s) FAILED - output:\n")
        for name, ok, _, _ in results:
            if not ok and name in outputs:
                print(f"--- {name} ---")
                print(outputs[name][-3000:])
        return 1

    print("\n ALL TEST GROUPS PASSED\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
