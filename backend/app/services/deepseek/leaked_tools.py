"""Recover tool calls that the model emits as plain text.

DeepSeek V3 (`deepseek-chat`) occasionally ignores the native function-calling
protocol and instead writes the tool call directly into the assistant message as
DSML / antml-style markup, e.g.::

    <｜DSML｜｜tool_calls｜>
    <｜DSML｜｜invoke name="update_diet_plan_item">
    <｜DSML｜｜parameter name="item_id" string="false">51<｜/｜｜DSML｜｜parameter>
    <｜DSML｜｜parameter name="status" string="true">confirmed<｜/｜｜DSML｜｜parameter>
    <｜/｜｜DSML｜｜invoke>
    <｜/｜｜DSML｜｜tool_calls>

When that happens the call is never executed and the raw markup leaks to the
user. This module parses those blocks so the caller can execute them for real.
"""

import re

# ``invoke name="tool_name"`` — tolerant of the surrounding token noise.
_INVOKE = re.compile(r'invoke\s+name\s*=\s*"([^"]+)"', re.IGNORECASE)
# ``parameter name="key" ...>value<`` — value runs up to the next tag.
_PARAM = re.compile(
    r'parameter\s+name\s*=\s*"([^"]+)"[^>]*>(.*?)<',
    re.IGNORECASE | re.DOTALL,
)


def _coerce(value: str) -> object:
    """Best-effort typing of a text parameter value (ints, floats, bools)."""
    s = value.strip()
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    return s


def parse_leaked_tool_calls(text: str | None) -> list[tuple[str, dict]]:
    """Extract (tool_name, arguments) pairs from leaked DSML/antml markup.

    Returns an empty list when the text contains no recognizable tool call.
    """
    if not text or "invoke" not in text.lower():
        return []

    calls: list[tuple[str, dict]] = []
    invokes = list(_INVOKE.finditer(text))
    for i, match in enumerate(invokes):
        name = match.group(1)
        start = match.end()
        end = invokes[i + 1].start() if i + 1 < len(invokes) else len(text)
        block = text[start:end]
        args = {key: _coerce(val) for key, val in _PARAM.findall(block)}
        calls.append((name, args))
    return calls
