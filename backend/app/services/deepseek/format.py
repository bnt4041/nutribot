"""Post-process assistant replies for clean rendering in Telegram."""

import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_BOLD_UNDERSCORE = re.compile(r"__(.+?)__", re.DOTALL)
_HEADER = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BULLET = re.compile(r"^(\s*)\*\s+", re.MULTILINE)
# DeepSeek V4 sometimes outputs raw tool-call blocks (DSML / XML) in the
# visible text instead of using the native function-calling protocol.
# Patterns cover multiple observed formats.
_DSML_TOOL_BLOCK = re.compile(
    r"(?:^|\n)DSML\s*\|[^\n]*",
    re.IGNORECASE,
)
_INVOKE_LINE = re.compile(
    r"^\s*(?:</?\s*invoke[^>]*>|invoke\s+name\s*=\s*\"[^\"]+\")\s*$",
    re.MULTILINE,
)
_PARAM_LINE = re.compile(
    r"^\s*(?:</?\s*parameter[^>]*>.*|parameter\s+name\s*=\s*\"[^\"]+\".*)\s*$",
    re.MULTILINE,
)
_XML_CLOSE = re.compile(r"</\s*(?:invoke|parameter)\s*>", re.IGNORECASE)


def sanitize_for_telegram(text: str) -> str:
    """Strip Markdown decoration and DSML tool-call blocks.

    The model sometimes emits Markdown despite instructions, and DeepSeek V4
    occasionally leaks raw tool-call syntax (DSML/XML) into the visible text.
    """
    # ── 1. Strip DSML / XML tool-call blocks ────────────────────────────
    text = _DSML_TOOL_BLOCK.sub("", text)
    text = _INVOKE_LINE.sub("", text)
    text = _PARAM_LINE.sub("", text)
    text = _XML_CLOSE.sub("", text)

    # ── 2. Strip Markdown ──────────────────────────────────────────────
    text = _MD_LINK.sub(r"\2", text)
    text = _BOLD.sub(r"\1", text)
    text = _BOLD_UNDERSCORE.sub(r"\1", text)
    text = _HEADER.sub("", text)
    text = _BULLET.sub(r"\1- ", text)

    # ── 3. Clean up blank lines left by stripped blocks ─────────────────
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
