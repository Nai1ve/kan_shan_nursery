"""Minimal YAML parser for our limited credential schema.

We avoid pulling PyYAML as a dependency so services stay stdlib-only.
The parser supports:
  - key: value (string, int, float, true/false, null/none, empty)
  - nested mappings via indentation (2-space)
  - lists of scalars via "- item" form
  - inline strings; quotes optional. Quoted strings (single or double)
    preserved literally.
  - "# ..." comments at end of line or whole line
It does NOT support multi-line strings, anchors, references, flow style,
or anything fancier. If a richer YAML is needed in the future, this can
be swapped for PyYAML behind the same load_config() entry point.
"""

from __future__ import annotations

import re
from typing import Any


_TRUE = {"true", "yes", "on"}
_FALSE = {"false", "no", "off"}
_NULL = {"null", "none", "~", ""}


def parse_yaml(text: str) -> dict[str, Any]:
    lines = []
    for raw_line in text.splitlines():
        stripped = _strip_inline_comment(raw_line)
        if stripped.strip() == "":
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError(f"YAML parse error: indentation must be multiples of 2 spaces: '{raw_line}'")
        lines.append((indent // 2, stripped.strip()))
    root: dict[str, Any] = {}
    _consume_block(lines, 0, 0, root)
    return root


def _strip_inline_comment(line: str) -> str:
    # Strip "# ..." but preserve "#" inside quoted strings (rare in our schema).
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def _consume_block(lines: list[tuple[int, str]], start: int, depth: int, target: dict[str, Any]) -> int:
    i = start
    while i < len(lines):
        indent, content = lines[i]
        if indent < depth:
            return i
        if indent > depth:
            raise ValueError(f"YAML parse error: unexpected indentation at '{content}'")
        if content.startswith("- "):
            raise ValueError("YAML parse error: list items must be the value of a key, not a top-level node")
        match = re.match(r"^([A-Za-z0-9_][A-Za-z0-9_\-]*)\s*:\s*(.*)$", content)
        if not match:
            raise ValueError(f"YAML parse error: expected 'key: value' but got '{content}'")
        key, raw_value = match.group(1), match.group(2).strip()
        if raw_value == "":
            # nested block: mapping or list (peek next line)
            if i + 1 < len(lines) and lines[i + 1][0] > depth:
                next_indent = lines[i + 1][0]
                if lines[i + 1][1].startswith("- "):
                    items, consumed = _consume_list(lines, i + 1, next_indent)
                    target[key] = items
                    i = consumed
                    continue
                child: dict[str, Any] = {}
                consumed = _consume_block(lines, i + 1, next_indent, child)
                target[key] = child
                i = consumed
                continue
            target[key] = None
            i += 1
            continue
        target[key] = _coerce(raw_value)
        i += 1
    return i


def _consume_list(lines: list[tuple[int, str]], start: int, depth: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    i = start
    while i < len(lines):
        indent, content = lines[i]
        if indent != depth or not content.startswith("- "):
            return items, i
        items.append(_coerce(content[2:].strip()))
        i += 1
    return items, i


def _coerce(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    lowered = value.lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    if lowered in _NULL:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
