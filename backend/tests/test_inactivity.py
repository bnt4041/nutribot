"""Tests for the inactivity-nudge decision logic (3+3+3 then one farewell)."""

import pytest

from app.services.inactivity import FAREWELL_MESSAGE, NUDGE_MESSAGE, compute_slot, message_for_slot


@pytest.mark.parametrize(
    "days_silent,nudge_count,expected",
    [
        (2.9, 0, None),  # not yet at the first 3-day mark
        (3.0, 0, 1),  # first nudge fires exactly at day 3
        (3.0, 1, None),  # already sent nudge 1; not due for nudge 2 yet
        (5.9, 1, None),
        (6.0, 1, 2),  # second nudge at day 6
        (9.0, 2, 3),  # third nudge at day 9
        (11.9, 3, None),  # sent all 3 nudges; farewell not due yet
        (12.0, 3, 4),  # farewell at day 12 (the 4th interval)
        (30.0, 4, None),  # farewell already sent; stays silent
    ],
)
def test_compute_slot_default_threshold(days_silent, nudge_count, expected):
    assert compute_slot(days_silent, threshold_days=3, nudge_count=nudge_count) == expected


def test_compute_slot_scales_with_threshold():
    # threshold=5 -> nudges at 5, 10, 15, farewell at 20.
    assert compute_slot(5.0, threshold_days=5, nudge_count=0) == 1
    assert compute_slot(19.9, threshold_days=5, nudge_count=3) is None
    assert compute_slot(20.0, threshold_days=5, nudge_count=3) == 4


def test_message_for_slot():
    assert message_for_slot(1) == NUDGE_MESSAGE
    assert message_for_slot(3) == NUDGE_MESSAGE
    assert message_for_slot(4) == FAREWELL_MESSAGE
