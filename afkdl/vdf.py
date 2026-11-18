"""Minimal, dependency-free parser for Valve VDF / ACF files."""

from __future__ import annotations

import re
from pathlib import Path

TOKEN_RE = re.compile(r'\s*(?:"((?:[^"\\]|\\.)*)"|([{}]))')


def _unescape(s: str) -> str:
    return s.replace("\\\\", "\\").replace('\\"', '"')


def parse_vdf(text: str) -> dict:
    """Turn VDF text into nested dicts. Returns partial data for truncated files."""
    root: dict = {}
    stack: list[dict] = [root]
    pending: str | None = None

    for m in TOKEN_RE.finditer(text):
        value, brace = m.group(1), m.group(2)
        if brace == "{":
            node: dict = {}
            if pending is not None:
                stack[-1][pending] = node
                pending = None
            stack.append(node)
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
            pending = None
        elif value is not None:
            if pending is None:
                pending = _unescape(value)
            else:
                stack[-1][pending] = _unescape(value)
                pending = None
    return root


def parse_vdf_file(path: Path) -> dict:
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return {}
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return parse_vdf(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    return parse_vdf(raw.decode("utf-8", "replace"))
