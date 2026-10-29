"""预约管理核心模块的单元测试（测试驱动开发 TDD —— 先写测试，再写实现）。

被测单元：app.services.appointment_rules
覆盖策略（实验二要求的主要功能 + 边界情况）：
  - 正常场景：提交合法预约
  - 边界值：今天/明天/第 30 天/第 31 天、容量剩余 1/已占满
  - 异常场景：过去日期、非法时段、服务已下架、重复预约
  - 状态机：预约状态流转（表驱动）
"""
from datetime import date, timedelta

import pytest

from app.services.appointment_rules import (
    AppointmentContext,
    can_cancel,
    can_transition,
    next_statuses,
    remaining_capacity,
    validate_new_appointment,
)

TODAY = date(2026, 10, 29)
TOMORROW = TODAY + timedelta(days=1)
VALID_SLOT = "09:00-10:00"


def make_context(online=True, capacity=5, used=0, duplicate=False):
    """构造预约上下文（模拟数据层查询结果，使业务规则可脱离数据库测试）。"""
    return AppointmentContext(
        service_online=online, capacity=capacity, used=used, has_duplicate=duplicate
    )


# ---------------------------------------------------------------- 正常与异常
def test_valid_appointment_has_no_errors():
    errors = validate_new_appointment(make_context(), TOMORROW, VALID_SLOT, today=TODAY)
    assert errors == []


def test_past_date_is_rejected():
    errors = validate_new_appointment(make_context(), TODAY - timedelta(days=1), VALID_SLOT, today=TODAY)
    assert any("不能预约过去的日期" in e for e in errors)


def test_today_is_allowed_boundary():
    """边界值：预约当天（today）应被允许。"""
    assert validate_new_appointment(make_context(), TODAY, VALID_SLOT, today=TODAY) == []


def test_last_allowed_day_boundary():
    """边界值：第 30 天（允许的最大值）应通过。"""
    assert validate_new_appointment(make_context(), TODAY + timedelta(days=30), VALID_SLOT, today=TODAY) == []


def test_day_31_is_rejected_boundary():
    """边界值：第 31 天（超出上限）应被拒绝。"""
    errors = validate_new_appointment(make_context(), TODAY + timedelta(days=31), VALID_SLOT, today=TODAY)
    assert any("30 天" in e for e in errors)


def test_invalid_time_slot_is_rejected():
    errors = validate_new_appointment(make_context(), TOMORROW, "25:00-26:00", today=TODAY)
    assert any("时段" in e for e in errors)


def test_offline_service_is_rejected():
    errors = validate_new_appointment(make_context(online=False), TOMORROW, VALID_SLOT, today=TODAY)
    assert any("已下架" in e for e in errors)


def test_duplicate_appointment_is_rejected():
    errors = validate_new_appointment(make_context(duplicate=True), TOMORROW, VALID_SLOT, today=TODAY)
    assert any("已预约" in e for e in errors)


# ---------------------------------------------------------------- 容量边界
def test_capacity_full_is_rejected():
    ctx = make_context(capacity=2, used=2)
    errors = validate_new_appointment(ctx, TOMORROW, VALID_SLOT, today=TODAY)
    assert any("已满" in e for e in errors)


def test_capacity_last_one_is_allowed():
    """边界值：只剩最后一个名额时应允许预约。"""
    ctx = make_context(capacity=2, used=1)
    assert validate_new_appointment(ctx, TOMORROW, VALID_SLOT, today=TODAY) == []


def test_remaining_capacity_calculation():
    assert remaining_capacity(capacity=5, used=2) == 3
    assert remaining_capacity(capacity=5, used=5) == 0
    assert remaining_capacity(capacity=3, used=9) == 0  # 超额占用时不出现负数


# ---------------------------------------------------------------- 状态机
@pytest.mark.parametrize(
    "current,new,expected",
    [
        ("pending", "confirmed", True),
        ("pending", "cancelled", True),
        ("confirmed", "completed", True),
        ("confirmed", "cancelled", True),
        ("pending", "completed", False),     # 不允许跨状态
        ("completed", "confirmed", False),   # 终态不可回退
        ("cancelled", "confirmed", False),   # 已取消不可复活
        ("completed", "completed", False),
    ],
)
def test_status_transition_table(current, new, expected):
    assert can_transition(current, new) is expected


def test_next_statuses_of_pending():
    assert set(next_statuses("pending")) == {"confirmed", "cancelled"}


def test_cancel_rules():
    assert can_cancel("pending") is True
    assert can_cancel("confirmed") is True
    assert can_cancel("completed") is False
    assert can_cancel("cancelled") is False


def test_unknown_status_is_rejected():
    assert can_transition("unknown", "confirmed") is False
    assert next_statuses("unknown") == []
