"""第三轮人工 β 测试（2026-11-23 20:43）回归用例：角色边界与按时段自动办结。

用户以管理员身份真实使用系统时提出三个问题：
  1. 管理员页面仍挂着「我的预约」「我的评价」等消费者入口（DEF-010）
  2. 后台管理应为主任务、优先级更高，且登录后应直接进后台（DEF-010）
  3. 「已完成」要在哪确认？预约时段结束就该自动完成，不该靠人工点（DEF-011）
  4. 管理员是服务提供方，不该能提交评价，但应能查看用户评价（DEF-010）

对应修复：
  - 角色化导航 + consumer_only 守卫 + 服务层纵深防御 + 管理员登录落地后台
  - 新增 is_slot_ended 纯函数与 auto_complete_due 惰性办结
  - 后台新增只读「评价查看」页
"""
from datetime import date, datetime, time, timedelta

import pytest

from app.extensions import db
from app.models import Appointment, Feedback
from app.services.appointment_rules import is_slot_ended
from app.services.appointment_service import auto_complete_due
from app.services.feedback_service import create_feedback, list_reviewable_appointments
from app.utils.contracts import ContractViolation

DAY = date(2026, 11, 23)
ENDED = datetime.combine(DAY, time(10, 0))       # 09:00-10:00 恰好结束
BEFORE_END = datetime.combine(DAY, time(9, 59))  # 尚未结束
LATE = datetime.combine(DAY, time(20, 43))


def _login(client, username, password):
    return client.post(
        "/auth/login", data={"login": username, "password": password}, follow_redirects=False
    )


def _make_appointment(user, service, day, slot, status="confirmed"):
    appt = Appointment(
        user_id=user.id,
        service_id=service.id,
        appointment_date=day,
        time_slot=slot,
        contact_name="李行",
        contact_phone="13800138000",
        status=status,
    )
    db.session.add(appt)
    db.session.commit()
    return appt


# ---------------------------------------------------------------- 规则层：is_slot_ended
def test_slot_ended_at_exact_end_time():
    """结束时刻一到即视为服务时段结束（半开区间取闭端）。"""
    assert is_slot_ended(DAY, "09:00-10:00", ENDED) is True


def test_slot_not_ended_one_minute_before():
    assert is_slot_ended(DAY, "09:00-10:00", BEFORE_END) is False


def test_slot_ended_later_today():
    assert is_slot_ended(DAY, "09:00-10:00", LATE) is True


def test_last_slot_ended_after_1700():
    assert is_slot_ended(DAY, "16:00-17:00", LATE) is True


def test_last_slot_not_ended_at_1659():
    assert is_slot_ended(DAY, "16:00-17:00", datetime.combine(DAY, time(16, 59))) is False


def test_past_date_always_ended():
    assert is_slot_ended(DAY - timedelta(days=1), "09:00-10:00", LATE) is True


def test_future_date_never_ended():
    assert is_slot_ended(DAY + timedelta(days=1), "09:00-10:00", LATE) is False


def test_invalid_slot_not_ended():
    """非法时段由预约校验负责报错，本函数不越权判定。"""
    assert is_slot_ended(DAY, "25:00-26:00", LATE) is False


def test_is_slot_ended_contract_rejects_bad_now():
    with pytest.raises(ContractViolation):
        is_slot_ended(DAY, "09:00-10:00", "2026-11-23 20:43")


def test_all_today_slots_ended_at_2043():
    assert all(is_slot_ended(DAY, slot, LATE) for slot in
               ("09:00-10:00", "10:00-11:00", "11:00-12:00",
                "14:00-15:00", "15:00-16:00", "16:00-17:00"))


# ---------------------------------------------------------------- 服务层：自动办结
def test_auto_complete_marks_ended_confirmed(app, normal_user, service):
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00")
    assert auto_complete_due(now=LATE) == 1
    assert Appointment.query.get(appt.id).status == "completed"


def test_auto_complete_skips_not_yet_ended(app, normal_user, service):
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00")
    assert auto_complete_due(now=BEFORE_END) == 0
    assert Appointment.query.get(appt.id).status == "confirmed"


def test_auto_complete_skips_pending(app, normal_user, service):
    """未受理的预约即使时段已过也不被时间直接推进为完成。"""
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00", status="pending")
    assert auto_complete_due(now=LATE) == 0
    assert Appointment.query.get(appt.id).status == "pending"


def test_auto_complete_skips_cancelled_and_completed(app, normal_user, service):
    cancelled = _make_appointment(normal_user, service, DAY, "09:00-10:00", status="cancelled")
    completed = _make_appointment(normal_user, service, DAY, "10:00-11:00", status="completed")
    auto_complete_due(now=LATE)
    assert Appointment.query.get(cancelled.id).status == "cancelled"
    assert Appointment.query.get(completed.id).status == "completed"


def test_auto_complete_is_idempotent(app, normal_user, service):
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00")
    assert auto_complete_due(now=LATE) == 1
    assert auto_complete_due(now=LATE) == 0
    assert Appointment.query.get(appt.id).status == "completed"


def test_auto_complete_past_date(app, normal_user, service):
    appt = _make_appointment(normal_user, service, DAY - timedelta(days=3), "09:00-10:00")
    assert auto_complete_due(now=LATE) == 1
    assert Appointment.query.get(appt.id).status == "completed"


def test_auto_complete_user_scope(app, normal_user, service, admin_user):
    """用户视图只办结本人预约，不触碰其他用户的数据。"""
    mine = _make_appointment(normal_user, service, DAY, "09:00-10:00")
    other = _make_appointment(admin_user, service, DAY, "10:00-11:00")
    assert auto_complete_due(now=LATE, user_id=normal_user.id) == 1
    assert Appointment.query.get(mine.id).status == "completed"
    assert Appointment.query.get(other.id).status == "confirmed"


def test_auto_complete_enables_review(app, normal_user, service):
    """时段结束自动办结后，评价资格随之开放（业务闭环）。"""
    _make_appointment(normal_user, service, DAY, "09:00-10:00")
    assert list_reviewable_appointments(normal_user) == []
    auto_complete_due(now=LATE)
    assert len(list_reviewable_appointments(normal_user)) == 1


def test_auto_complete_uses_current_time_by_default(app, normal_user, service):
    """不注入时刻时取系统当前时间：未来日期的预约不会被误办结。"""
    appt = _make_appointment(normal_user, service, date.today() + timedelta(days=3), "09:00-10:00")
    assert auto_complete_due() == 0
    assert Appointment.query.get(appt.id).status == "confirmed"


def test_auto_complete_mixed_batch(app, normal_user, service):
    """同一批次里既有已结束、也有未结束、还有不属于本人的：只办结该办结的。"""
    ended = _make_appointment(normal_user, service, DAY, "09:00-10:00")
    future = _make_appointment(normal_user, service, DAY + timedelta(days=1), "09:00-10:00")
    assert auto_complete_due(now=LATE) == 1
    assert Appointment.query.get(ended.id).status == "completed"
    assert Appointment.query.get(future.id).status == "confirmed"


# ---------------------------------------------------------------- 角色化导航
def test_admin_nav_has_backend_first_and_no_consumer_links(client, admin_user, service):
    _login(client, "admin", "Admin@123")
    body = client.get("/").get_data(as_text=True)
    assert 'class="nav-feature"' in body and "后台管理" in body
    assert "我的预约" not in body
    assert "我的评价" not in body
    # 主任务入口排在导航最前
    assert body.index('class="nav-feature"') < body.index("服务查询")


def test_normal_user_nav_has_consumer_links_and_no_backend(client, normal_user, service):
    _login(client, "zhangsan", "User@123")
    body = client.get("/").get_data(as_text=True)
    assert "我的预约" in body and "我的评价" in body
    assert "后台管理" not in body


def test_anonymous_nav_is_public_only(client):
    body = client.get("/").get_data(as_text=True)
    assert "我的预约" not in body and "后台管理" not in body


def test_admin_role_tag_visible(client, admin_user):
    _login(client, "admin", "Admin@123")
    assert 'class="role-tag role-admin"' in client.get("/").get_data(as_text=True)


# ---------------------------------------------------------------- 登录落地页
def test_admin_login_lands_on_backend(client, admin_user):
    resp = _login(client, "admin", "Admin@123")
    assert resp.status_code == 302
    assert "/admin/" in resp.headers["Location"]


def test_normal_user_login_lands_on_home(client, normal_user):
    resp = _login(client, "zhangsan", "User@123")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_admin_login_respects_safe_next(client, admin_user):
    """next 参数优先级高于角色化落地，且开放重定向防护不变。"""
    resp = client.post("/auth/login?next=/admin/users",
                       data={"login": "admin", "password": "Admin@123"})
    assert "/admin/users" in resp.headers["Location"]


def test_admin_login_ignores_external_next(client, admin_user):
    resp = client.post("/auth/login?next=https://evil.example.com",
                       data={"login": "admin", "password": "Admin@123"})
    assert resp.headers["Location"].startswith("/")
    assert "evil.example.com" not in resp.headers["Location"]


# ---------------------------------------------------------------- 消费者页面守卫
@pytest.mark.parametrize("path", ["/appointments/mine", "/feedback/mine", "/feedback/create"])
def test_admin_consumer_pages_redirect_to_backend(client, admin_user, service, path):
    _login(client, "admin", "Admin@123")
    resp = client.get(path)
    assert resp.status_code == 302
    assert "/admin/" in resp.headers["Location"]


@pytest.mark.parametrize("path", ["/appointments/mine", "/feedback/mine"])
def test_normal_user_consumer_pages_allowed(client, normal_user, service, path):
    _login(client, "zhangsan", "User@123")
    assert client.get(path).status_code == 200


def test_admin_cancel_post_blocked(client, admin_user, service, normal_user):
    appt = _make_appointment(normal_user, service, DAY + timedelta(days=1), "09:00-10:00")
    _login(client, "admin", "Admin@123")
    resp = client.post(f"/appointments/{appt.id}/cancel")
    assert resp.status_code == 302
    assert Appointment.query.get(appt.id).status == "confirmed"


# ---------------------------------------------------------------- 服务层：管理员不可评价
def test_admin_cannot_create_feedback(app, admin_user, normal_user, service):
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00", status="completed")
    fb, reason = create_feedback(admin_user, appt, 5, "管理员评价")
    assert fb is None and "管理员" in reason
    assert Feedback.query.count() == 0


def test_admin_create_feedback_does_not_write_db(app, admin_user, normal_user, service):
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00", status="completed")
    create_feedback(admin_user, appt, 4, "x")
    assert Feedback.query.count() == 0


def test_normal_user_can_create_feedback(app, normal_user, service):
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00", status="completed")
    fb, reason = create_feedback(normal_user, appt, 5, "服务很好")
    assert fb is not None and reason == ""
    assert Feedback.query.count() == 1


@pytest.mark.parametrize("bad_rating", [0, 6, -1, "5", 5.0])
def test_create_feedback_rejects_invalid_rating(app, normal_user, service, bad_rating):
    """评分边界与类型校验：非法评分不写库（教材边界值分析）。"""
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00", status="completed")
    fb, reason = create_feedback(normal_user, appt, bad_rating, "评分非法")
    assert fb is None and "评分" in reason
    assert Feedback.query.count() == 0


# ---------------------------------------------------------------- 后台只读评价页
def test_admin_feedbacks_page_is_read_only(client, admin_user, normal_user, service):
    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00", status="completed")
    db.session.add(Feedback(user_id=normal_user.id, service_id=service.id,
                            appointment_id=appt.id, rating=5, content="效率高"))
    db.session.commit()
    _login(client, "admin", "Admin@123")
    body = client.get("/admin/feedbacks").get_data(as_text=True)
    assert "效率高" in body and "评价查看" in body
    assert "提交新评价" not in body
    assert "只读" in body


def test_normal_user_cannot_access_admin_feedbacks(client, normal_user):
    _login(client, "zhangsan", "User@123")
    assert client.get("/admin/feedbacks").status_code == 403


# ---------------------------------------------------------------- 视图触发自动办结
def test_admin_appointments_page_triggers_auto_complete(client, admin_user, normal_user, service,
                                                        monkeypatch):
    """管理员打开预约管理页时，到期预约被自动办结（固定时钟，不依赖运行时刻）。"""
    import app.services.appointment_service as svc

    appt = _make_appointment(normal_user, service, DAY, "09:00-10:00")
    monkeypatch.setattr(svc, "datetime", type("FakeDatetime", (), {
        "now": staticmethod(lambda: LATE)
    }))
    _login(client, "admin", "Admin@123")
    body = client.get("/admin/appointments").get_data(as_text=True)
    assert Appointment.query.get(appt.id).status == "completed"
    assert "自动办结" in body


def test_user_mine_page_triggers_own_auto_complete(client, normal_user, admin_user, service,
                                                  monkeypatch):
    """用户看自己的列表时只办结本人预约。"""
    import app.services.appointment_service as svc

    mine = _make_appointment(normal_user, service, DAY, "09:00-10:00")
    other = _make_appointment(admin_user, service, DAY, "10:00-11:00")
    monkeypatch.setattr(svc, "datetime", type("FakeDatetime", (), {
        "now": staticmethod(lambda: LATE)
    }))
    _login(client, "zhangsan", "User@123")
    client.get("/appointments/mine")
    assert Appointment.query.get(mine.id).status == "completed"
    assert Appointment.query.get(other.id).status == "confirmed"


# ---------------------------------------------------------------- 后台页面说明
def test_admin_appointments_page_explains_completion(client, admin_user):
    _login(client, "admin", "Admin@123")
    body = client.get("/admin/appointments").get_data(as_text=True)
    assert "在哪里确认" in body
    assert "自动办结" in body
    assert "推进状态" in body


def test_dashboard_has_feedbacks_entry(client, admin_user):
    _login(client, "admin", "Admin@123")
    body = client.get("/admin/").get_data(as_text=True)
    assert "评价查看" in body
    assert "管理与发布" in body
