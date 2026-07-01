"""Post-process assistant replies for clean rendering in Telegram."""

import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_BOLD_UNDERSCORE = re.compile(r"__(.+?)__", re.DOTALL)
_HEADER = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BULLET = re.compile(r"^(\s*)\*\s+", re.MULTILINE)


def sanitize_for_telegram(text: str) -> str:
    """Strip Markdown decoration the model sometimes emits despite instructions.

    Converts Markdown links to their raw URL (so Telegram renders a link
    preview), removes bold markers and headings, and turns ``* `` bullets into
    ``- ``. Kept deliberately conservative to avoid mangling legitimate content.
    """
    # Keep the raw URL so Telegram can show the product preview/image.
    text = _MD_LINK.sub(r"\2", text)
    text = _BOLD.sub(r"\1", text)
    text = _BOLD_UNDERSCORE.sub(r"\1", text)
    text = _HEADER.sub("", text)
    text = _BULLET.sub(r"\1- ", text)
    return text
