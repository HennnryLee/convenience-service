"""DEF-008 / DEF-009 回归用例：当日已过时段拦截、管理员预约权限。

对应人工 β 测试（2026-11-23 18:04）发现的三个业务问题：
  1. 管理员账号可在前台提交预约 —— 权限控制缺失；
  2. 当天已经开始的时段仍可预约 —— 时间边界校验缺失；
  3. 「已完成」的确认机制为管理员办结推进（状态机），见后台页面说明与文档。
"""
from datetime import date, datetime, time, timedelta

import pytest

from app.models import Appointment
from app.services.appointment_rules import is_slot_started
from app.services.appointment_service import create_appointment, get_slot_availability
from app.utils.constants import TIME_SLOTS
from app.utils.contracts import ContractViolation

# 基准日期取「今天」：写死某一天会在跨天后被「过去日期」校验正确拦截，造成假失败。
# 「时段是否已开始」一律由显式注入的 LATE / EARLY 决定，与真实运行时刻无关，用例可重复执行。
DAY = date.today()
LATE = datetime.combine(DAY, time(18, 4))     # 所有时段都已开始
EARLY = datetime.combine(DAY, time(8, 30))    # 09:00 时段尚未开始


def _book(user, service, day, slot="09:00-10:00", now=None):
    return create_appointment(
        user=user,
        service_id=service.id,
        appointment_date=day,
        time_slot=slot,
        contact_name="张三",
        contact_phone="13800138000",
        now=now,
    )


def _login(client, username, password):
    return client.post(
        "/auth/login", data={"login": username, "password": password}, follow_redirects=True
    )


# ---------------------------------------------------------------- 规则层：is_slot_started
def test_is_slot_started_true_after_start_time():
    assert is_slot_started(DAY, "09:00-10:00", LATE) is True


def test_is_slot_started_false_before_start_time():
    assert is_slot_started(DAY, "09:00-10:00", EARLY) is False


def test_is_slot_started_true_at_exact_start():
    """开始时刻一到即不可再预约（不能预约正在进行的时段）。"""
    assert is_slot_started(DAY, "09:00-10:00", datetime.combine(DAY, time(9, 0))) is True


def test_is_slot_started_last_slot_at_1804():
    assert is_slot_started(DAY, "16:00-17:00", LATE) is True


def test_is_slot_started_future_date_ignored():
    assert is_slot_started(DAY + timedelta(days=1), "09:00-10:00", LATE) is False


def test_is_slot_started_invalid_slot_ignored():
    """无效时段由 validate_new_appointment 报错，这里不越权判定。"""
    assert is_slot_started(DAY, "25:00-26:00", LATE) is False


def test_all_today_slots_are_past_at_1804():
    assert all(is_slot_started(DAY, slot, LATE) for slot in TIME_SLOTS)


def test_is_slot_started_contract_rejects_bad_now():
    with pytest.raises(ContractViolation):
        is_slot_started(DAY, "09:00-10:00", "2026-11-23 18:04")


# ---------------------------------------------------------------- 服务层：已过时段
def test_today_past_slot_rejected(app, normal_user, service):
    appt, errors = _book(normal_user, service, DAY, "16:00-17:00", now=LATE)
    assert appt is None
    assert any("已开始或已过" in e for e in errors)


def test_today_past_slot_does_not_write_db(app, normal_user, service):
    _book(normal_user, service, DAY, "16:00-17:00", now=LATE)
    assert Appointment.query.count() == 0


def test_today_not_yet_started_slot_allowed(app, normal_user, service):
    appt, errors = _book(normal_user, service, DAY, "09:00-10:00", now=EARLY)
    assert errors == [] and appt is not None


def test_future_day_booking_allowed_even_late_today(app, normal_user, service):
    appt, errors = _book(normal_user, service, DAY + timedelta(days=1), "09:00-10:00", now=LATE)
    assert errors == [] and appt is not None


def test_past_date_still_rejected_by_rule_layer(app, normal_user, service):
    appt, errors = _book(normal_user, service, DAY - timedelta(days=1), "09:00-10:00", now=LATE)
    assert appt is None and any("过去" in e for e in errors)


# ---------------------------------------------------------------- 服务层：管理员权限
def test_admin_cannot_book(app, admin_user, service):
    appt, errors = _book(admin_user, service, DAY + timedelta(days=1))
    assert appt is None
    assert any("管理员" in e for e in errors)


def test_admin_booking_does_not_write_db(app, admin_user, service):
    _book(admin_user, service, DAY + timedelta(days=1))
    assert Appointment.query.count() == 0


def test_role_check_precedes_time_check(app, admin_user, service):
    """管理员即便选了已过时段，也应先被权限拦截，而不是返回时段错误。"""
    _, errors = _book(admin_user, service, DAY, "16:00-17:00", now=LATE)
    assert any("管理员" in e for e in errors)
    assert not any("已开始" in e for e in errors)


def test_normal_user_can_book_as_control(app, normal_user, service):
    appt, errors = _book(normal_user, service, DAY + timedelta(days=1))
    assert errors == [] and appt is not None


# ---------------------------------------------------------------- 展示层：时段可用性
def test_availability_marks_past_slots(app, service):
    items = get_slot_availability(service, DAY, now=LATE)
    assert len(items) == len(TIME_SLOTS)
    assert all(item["past"] is True for item in items)


def test_availability_without_now_is_backward_compatible(app, service):
    items = get_slot_availability(service, DAY)
    assert all(item["past"] is False for item in items)


def test_availability_future_day_not_marked_past(app, service):
    items = get_slot_availability(service, DAY + timedelta(days=1), now=LATE)
    assert all(item["past"] is False for item in items)


# ---------------------------------------------------------------- 视图层：管理员访问预约页
def test_admin_get_create_page_redirected(client, admin_user, service):
    _login(client, "admin", "Admin@123")
    resp = client.get(f"/appointments/create/{service.id}", follow_redirects=True)
    assert "不可提交预约".encode() in resp.data


def test_admin_post_booking_rejected_and_no_record(client, admin_user, service):
    _login(client, "admin", "Admin@123")
    resp = client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": (DAY + timedelta(days=1)).strftime("%Y-%m-%d"),
              "time_slot": "09:00-10:00", "contact_name": "张三",
              "contact_phone": "13800138000"},
        follow_redirects=True,
    )
    assert "不可提交预约".encode() in resp.data
    assert Appointment.query.count() == 0


def test_service_detail_hides_booking_button_for_admin(client, admin_user, service):
    _login(client, "admin", "Admin@123")
    resp = client.get(f"/services/{service.id}")
    assert "不可提交预约".encode() in resp.data
    assert "立即预约".encode() not in resp.data


def test_service_detail_shows_booking_button_for_normal_user(client, normal_user, service):
    _login(client, "zhangsan", "User@123")
    resp = client.get(f"/services/{service.id}")
    assert "立即预约".encode() in resp.data


# ---------------------------------------------------------------- 详情服务：注入当前时刻
def test_service_detail_marks_today_slots_as_past(app, service, monkeypatch):
    """详情页「今日各时段」在 18:04 时全部标记为已过（固定时钟，避免依赖运行时刻）。"""
    import app.services.service_catalog as catalog

    class FakeDatetime:
        @staticmethod
        def now():
            return datetime.combine(date.today(), time(18, 4))

    monkeypatch.setattr(catalog, "datetime", FakeDatetime)
    detail = catalog.get_service_detail(service.id)
    assert detail is not None
    assert len(detail["availability"]) == len(TIME_SLOTS)
    assert all(item["past"] is True for item in detail["availability"])
