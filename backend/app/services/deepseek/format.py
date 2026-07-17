"""Post-process assistant replies for clean rendering in Telegram."""

import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_BOLD_UNDERSCORE = re.compile(r"__(.+?)__", re.DOTALL)
_HEADER = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BULLET = re.compile(r"^(\s*)\*\s+", re.MULTILINE)
# GFM table separator row, e.g. "|---|:--:|---|" or "---|---" (no outer pipes).
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
# DeepSeek V3/V4 sometimes outputs raw tool-call blocks (DSML / antml / XML) in
# the visible text instead of using the native function-calling protocol. The
# client recovers and executes these (see leaked_tools.py); this sanitizer is the
# final net that removes any residual markup before it reaches the user.
#
# The tags come wrapped in special-token noise like ``<｜DSML｜｜tool_calls｜>``
# (fullwidth pipes) or the ASCII ``< | DSML | | tool_calls>`` rendering, so the
# patterns key off the inner keyword and swallow whatever brackets it.
#
# 1. Whole ``tool_calls`` block: from the opening tag to the closing one.
_TOOLCALL_BLOCK = re.compile(
    r"<[^>]*tool_calls[^>]*>.*?<[^>]*tool_calls[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
# 2. Whole ``invoke`` block (in case the outer tool_calls wrapper is absent).
_INVOKE_BLOCK = re.compile(
    r"<[^>]*\binvoke\b[^>]*>.*?<[^>]*/[^>]*\binvoke\b[^>]*>",
    re.IGNORECASE | re.DOTALL,
)
# 3. Any residual individual tag referencing the tool-call vocabulary.
_RESIDUAL_TAG = re.compile(
    r"<[^>]*(?:DSML|antml|tool_calls?|invoke|parameter)[^>]*>",
    re.IGNORECASE,
)


def _split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _convert_tables(text: str) -> str:
    """Turn GFM pipe tables into plain lines Telegram can actually render.

    The model is told not to use tables, but DeepSeek occasionally emits one
    anyway; without this, Telegram shows the raw "| a | b |" / "|---|---|"
    syntax verbatim. Each data row becomes "<label> — <header>: <value> · ...",
    using the first column as the row label.
    """
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" in line and i + 1 < len(lines) and _TABLE_SEPARATOR.match(lines[i + 1]):
            header = _split_table_row(line)
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                row = _split_table_row(lines[i])
                label = row[0] if row else ""
                pairs = [
                    f"{h}: {v}" if h else v
                    for h, v in zip(header[1:], row[1:])
                    if v
                ]
                if label and pairs:
                    out.append(f"{label} — {' · '.join(pairs)}")
                elif label or pairs:
                    out.append(label or " · ".join(pairs))
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def sanitize_for_telegram(text: str) -> str:
    """Strip Markdown decoration and DSML tool-call blocks.

    The model sometimes emits Markdown despite instructions, and DeepSeek V4
    occasionally leaks raw tool-call syntax (DSML/XML) into the visible text.
    """
    # ── 1. Strip DSML / antml / XML tool-call markup ────────────────────
    text = _TOOLCALL_BLOCK.sub("", text)
    text = _INVOKE_BLOCK.sub("", text)
    text = _RESIDUAL_TAG.sub("", text)

    # ── 2. Strip Markdown ──────────────────────────────────────────────
    text = _convert_tables(text)
    text = _MD_LINK.sub(r"\2", text)
    text = _BOLD.sub(r"\1", text)
    text = _BOLD_UNDERSCORE.sub(r"\1", text)
    text = _HEADER.sub("", text)
    text = _BULLET.sub(r"\1- ", text)

    # ── 3. Clean up blank lines left by stripped blocks ─────────────────
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
