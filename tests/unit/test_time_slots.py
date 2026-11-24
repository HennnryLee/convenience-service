"""时段解析纯函数测试（边界值 + 等价类）。

被测单元：`app.utils.time_slots.parse_slot / is_known_slot / now_minutes`。
它是预约时间规则的单一事实来源，必须覆盖格式、范围、先后顺序与非法输入。
"""
from datetime import date, datetime

import pytest
from app.utils.constants import TIME_SLOTS
from app.utils.time_slots import (
    is_known_slot,
    now_minutes,
    parse_slot,
    slot_end,
    slot_start,
)


@pytest.mark.parametrize("slot", TIME_SLOTS)
def test_all_configured_slots_parse_to_ordered_bounds(slot):
    bounds = parse_slot(slot)
    assert bounds is not None
    start, end = bounds
    assert 0 <= start < end <= 24 * 60


def test_parse_slot_normal_values():
    assert parse_slot("09:00-10:00") == (9 * 60, 10 * 60)
    assert parse_slot("14:30-16:15") == (14 * 60 + 30, 16 * 60 + 15)


@pytest.mark.parametrize(
    "slot",
    [
        None,
        123,
        "",
        "09:00",
        "09:00-10:00-11:00",
        "9:00-10:00",
        "09:60-10:00",
        "24:00-25:00",
        "10:00-10:00",
        "11:00-10:00",
        "ab:cd-ef:gh",
    ],
)
def test_parse_slot_rejects_invalid_input(slot):
    assert parse_slot(slot) is None


def test_known_slot_only_accepts_configured_values():
    assert is_known_slot("09:00-10:00") is True
    assert is_known_slot("08:00-09:00") is False
    assert is_known_slot(None) is False


def test_now_minutes_converts_clock_to_day_offset():
    assert now_minutes(datetime(2026, 1, 1, 0, 0)) == 0
    assert now_minutes(datetime(2026, 1, 1, 9, 30)) == 9 * 60 + 30
    assert now_minutes(datetime(2026, 1, 1, 23, 59)) == 23 * 60 + 59


def test_slot_start_and_end_helpers():
    assert slot_start("09:00-10:00") == 9 * 60
    assert slot_end("09:00-10:00") == 10 * 60
    assert slot_start("invalid") is None
    assert slot_end(None) is None


def test_parse_slot_is_pure_and_does_not_touch_date():
    before = date.today()
    assert parse_slot("09:00-10:00") == (540, 600)
    assert date.today() == before
