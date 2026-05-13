from __future__ import annotations

import re
from html import escape
from typing import Any


_INLINE_MATH_RE = re.compile(r"(?<!\\)\$(?![\d\s])(.+?)(?<![\s\\])\$")
_DISPLAY_MATH_RE = re.compile(r"(?<!\\)\$\$(.+?)(?<!\\)\$\$", re.DOTALL)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _format_plain_segment(text: str) -> str:
    safe = escape(text)
    safe = _BOLD_RE.sub(r"<strong>\1</strong>", safe)
    return safe.replace("\n", "<br>")


def _format_plain_with_inline_math(text: str) -> str:
    parts: list[str] = []
    pos = 0
    for match in _INLINE_MATH_RE.finditer(text):
        if match.start() > pos:
            parts.append(_format_plain_segment(text[pos : match.start()]))
        expr = escape(match.group(1).strip())
        parts.append(f'<span class="math-inline">{expr}</span>')
        pos = match.end()
    if pos < len(text):
        parts.append(_format_plain_segment(text[pos:]))
    return "".join(parts)


def format_long_text_html(content: Any) -> str:
    """Escape model text while preserving structure and readable math.

    Streamlit's native math rendering does not apply inside our custom chat
    HTML. This gives LaTeX snippets a stable readable fallback even when the
    optional KaTeX script is blocked by the browser sandbox.
    """
    raw = str(content or "")
    parts: list[str] = []
    pos = 0

    for match in _DISPLAY_MATH_RE.finditer(raw):
        if match.start() > pos:
            parts.append(_format_plain_with_inline_math(raw[pos : match.start()]))
        expr = escape(match.group(1).strip())
        parts.append(f'<div class="math-block">{expr}</div>')
        pos = match.end()

    if pos < len(raw):
        parts.append(_format_plain_with_inline_math(raw[pos:]))

    return "".join(parts)
