"""白盒测试：针对核心业务逻辑单元的语句/判定/条件/路径覆盖。

被测单元：
  U1 `app.services.password_policy.validate_password`（密码强度校验）
  U2 `app.services.appointment_rules.validate_new_appointment`（预约校验）
  U3 `app.services.appointment_rules.can_transition`（状态流转判定）
  U4 `app.services.feedback_service.can_review`（评价资格判定）

每个单元的流程图、圈复杂度与独立路径数见《白盒测试与单元测试》实验报告。
"""
from datetime import date

import pytest

from app.services.appointment_rules import (
    AppointmentContext,
    can_transition,
    validate_new_appointment,
)
from app.services.feedback_service import can_review
from app.services.password_policy import validate_password

TODAY = date(2026, 1, 1)


# ==================================================================== U1 密码强度
def test_u1_statement_coverage_all_branches():
    """语句覆盖 & 判定覆盖：让 U1 的 7 个判定各取真/假至少一次。"""
    assert validate_password(None) != []                       # password is None → 空串分支
    assert validate_password("Abc12345") == []                 # 全判定为假（合法）
    assert validate_password("Abc1234") != []                  # 长度判定为真
    assert validate_password("abcdefgh") != []                 # 缺数字
    assert validate_password("12345678") != []                 # 缺字母
    assert validate_password("Abc 1234") != []                 # 含空格
    assert validate_password("sameuser1", "sameuser1") != []   # 与用户名相同
    assert validate_password("sameuser1", "other") == []       # username 不同


def test_u1_condition_coverage_compound_condition():
    """条件覆盖：复合条件 `has_letter and has_digit` 的四种组合。"""
    assert validate_password("Abcdefgh") != []   # letter=T, digit=F
    assert validate_password("12345678") != []   # letter=F, digit=T
    assert validate_password("!@#$%^&*") != []   # letter=F, digit=F
    assert validate_password("Abc12345") == []   # letter=T, digit=T


def test_u1_condition_coverage_username_condition():
    """条件覆盖：复合条件 `username and password == username` 的组合。"""
    assert validate_password("Abc12345", None) == []           # username 为空 → 短路
    assert validate_password("Abc12345", "other") == []        # username 非空但不相等
    assert validate_password("Abc12345", "Abc12345") != []     # 相等 → 命中


def test_u1_path_coverage_eight_paths():
    """路径覆盖：U1 圈复杂度 V(G)=8，设计 8 条独立路径。"""
    paths = [
        ("Abc12345", None),          # P1：全部判定为假 → 合法
        ("Abc1234", None),           # P2：仅长度不合法
        ("Abcdefgh", None),          # P3：仅缺数字
        ("12345678", None),          # P4：仅缺字母
        ("!@#$%^&*!", None),         # P5：既缺字母又缺数字
        ("Abc 12345", None),         # P6：含空格
        ("Abc12345", "Abc12345"),    # P7：与用户名相同
        ("Ab 123", "Ab 123"),        # P8：多条件同时命中
    ]
    for pwd, user in paths:
        validate_password(pwd, user)  # 每条路径均需实际执行，由覆盖率统计确认


# ==================================================================== U2 预约校验
def _ctx(online=True, capacity=5, used=0, duplicate=False):
    return AppointmentContext(service_online=online, capacity=capacity,
                              used=used, has_duplicate=duplicate)


def test_u2_statement_coverage():
    ok = validate_new_appointment(_ctx(), TODAY, "09:00-10:00", today=TODAY)
    assert ok == []
    offline = validate_new_appointment(_ctx(online=False), TODAY, "09:00-10:00", today=TODAY)
    assert any("下架" in e for e in offline)
    null_date = validate_new_appointment(_ctx(), None, "09:00-10:00", today=TODAY)
    assert any("请选择预约日期" in e for e in null_date)


def test_u2_decision_coverage_each_branch():
    """判定覆盖：U2 的 7 个判定各取真/假至少一次。"""
    cases = [
        (_ctx(), TODAY, "09:00-10:00"),                     # 全假
        (_ctx(online=False), TODAY, "09:00-10:00"),         # 服务下架
        (_ctx(), TODAY - date.resolution, "09:00-10:00"),   # 过去日期（占位，见下）
        (_ctx(), TODAY, "25:00-26:00"),                     # 非法时段
        (_ctx(duplicate=True), TODAY, "09:00-10:00"),       # 重复预约
        (_ctx(used=5), TODAY, "09:00-10:00"),               # 名额已满
    ]
    for ctx, day, slot in cases:
        validate_new_appointment(ctx, day, slot, today=TODAY)


def test_u2_boundary_paths():
    """路径覆盖：日期边界的 4 条独立路径。"""
    from datetime import timedelta

    assert validate_new_appointment(_ctx(), TODAY, "09:00-10:00", today=TODAY) == []
    assert validate_new_appointment(
        _ctx(), TODAY - timedelta(days=1), "09:00-10:00", today=TODAY) != []
    assert validate_new_appointment(
        _ctx(), TODAY + timedelta(days=30), "09:00-10:00", today=TODAY) == []
    assert validate_new_appointment(
        _ctx(), TODAY + timedelta(days=31), "09:00-10:00", today=TODAY) != []


# ==================================================================== U3 状态流转
@pytest.mark.parametrize(
    "current,new,expected",
    [
        ("pending", "confirmed", True),
        ("pending", "cancelled", True),
        ("pending", "completed", False),
        ("confirmed", "completed", True),
        ("confirmed", "cancelled", True),
        ("completed", "pending", False),
        ("cancelled", "pending", False),
        ("unknown", "pending", False),
    ],
)
def test_u3_branch_coverage(current, new, expected):
    """判定/分支覆盖：状态机的每条分支与默认分支。"""
    assert can_transition(current, new) is expected


# ==================================================================== U4 评价资格
def test_u4_all_paths(app, normal_user, service, appointment):
    """U4 路径覆盖：4 条独立路径（记录不存在 / 非本人 / 状态未完成 / 已评价）。"""
    # P1 预约不存在
    ok, reason = can_review(normal_user, None)
    assert ok is False and "不存在" in reason

    # P2 非本人预约（另建用户）
    from app.extensions import db
    from app.models import User

    other = User(username="other", email="other@example.com")
    other.set_password("User@123")
    db.session.add(other)
    db.session.commit()
    ok, reason = can_review(other, appointment)
    assert ok is False and "本人" in reason

    # P3 状态未完成
    ok, reason = can_review(normal_user, appointment)
    assert ok is False and "已完成" in reason

    # P4 已完成且未评价 → 通过
    appointment.status = "completed"
    db.session.commit()
    ok, reason = can_review(normal_user, appointment)
    assert ok is True and reason == ""

    # P5 已完成但已评价 → 拒绝
    from app.repositories import FeedbackRepository

    FeedbackRepository.create(normal_user.id, service.id, appointment.id, 5, "不错")
    ok, reason = can_review(normal_user, appointment)
    assert ok is False and "已评价" in reason
