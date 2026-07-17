"""Inactivity nudge: re-engage users who've gone quiet on Telegram.

Fires up to 3 nudges, spaced `inactivity_reminder_days` apart (e.g. 3+3+3 with
the default), then a one-time farewell after the 4th interval — after that we
stay silent until the user chats again, which resets the streak.
"""

MAX_NUDGES = 3

NUDGE_MESSAGE = (
    "🙋 Hace unos días que no hablamos. ¿Seguimos con tu plan? Aquí estoy "
    "cuando quieras retomarlo."
)
FAREWELL_MESSAGE = (
    "👋 Ha pasado bastante tiempo sin noticias tuyas, así que voy a dejar de "
    "escribirte por ahora. Cuando quieras retomarlo, aquí me tienes — solo "
    "mándame un mensaje."
)


def compute_slot(days_silent: float, threshold_days: int, nudge_count: int) -> int | None:
    """Which inactivity message (1..MAX_NUDGES+1) is due right now, if any.

    Slots 1..MAX_NUDGES are nudges, fired once each as ``days_silent`` crosses
    each multiple of ``threshold_days``. Slot MAX_NUDGES+1 is the one-time
    farewell. Once ``nudge_count`` reaches that, nothing fires again until the
    caller resets it (the user chatted, restarting the silent streak).
    """
    if nudge_count > MAX_NUDGES:
        return None
    next_slot = nudge_count + 1
    if days_silent >= threshold_days * next_slot:
        return next_slot
    return None


def message_for_slot(slot: int) -> str:
    return FAREWELL_MESSAGE if slot > MAX_NUDGES else NUDGE_MESSAGE
