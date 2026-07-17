"""Detect replies that claim a mutation happened without any tool call.

DeepSeek V3 sometimes narrates a fake tool call in plain, well-formed Spanish
prose ("Voy a consultar el plan... Lo actualizo... Hecho ✅") and returns it as
the final answer without ever invoking a function. Nothing about that text is
malformed — it just isn't backed by a real action — so it can't be caught by
the DSML/antml markup parser. This module gives ``chat_with_tools`` a way to
notice the pattern and force a real tool round instead of trusting the claim.
"""

import re

# Phrases that, in this domain, only make sense after a real tool call
# succeeded (confirming, saving, updating or deleting something for the user).
_CLAIMED_MUTATION = re.compile(
    r"\b("
    r"hecho|listo|actualizad[oa]|confirmad[oa]|guardad[oa]|registrad[oa]|"
    r"eliminad[oa]|añadid[oa]|borrad[oa]"
    r")\b",
    re.IGNORECASE,
)
# Narration of internal steps ("voy a ver los ids", "primero consulto...") that
# should never appear in a user-facing reply — a strong tell of the same bug.
_NARRATED_STEPS = re.compile(
    r"\b(voy a (?:consultar|ver|revisar|modificar|actualizar|comprobar)|"
    r"primero (?:veo|consulto|reviso)|"
    r"tiene id \d+|\bid[:\s]+\d+\b|"
    r"lo actualizo\b|calculo macros)\b",
    re.IGNORECASE,
)


def looks_like_unbacked_action_claim(text: str) -> bool:
    """True if ``text`` reads like a completed mutation with no tool call behind it.

    Only call this when the model's turn produced zero tool calls (native and
    leaked); it is not meant to flag every message containing these words.
    """
    if not text:
        return False
    return bool(_CLAIMED_MUTATION.search(text) or _NARRATED_STEPS.search(text))
