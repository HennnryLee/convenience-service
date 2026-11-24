"""管理员/普通用户角色与功能一致性回归。

对应 docs/17-角色与功能一致性矩阵.md：
  - 管理员只管理普通用户，不管理其他管理员；
  - 下架服务不对外展示；
  - 普通用户不能在预约时段开始后取消，管理员可处理异常；
  - 消费者页面与后台页面互不越权。
"""
from datetime import date, datetime, time, timedelta

from app.extensions import db
from app.services.appointment_service import cancel_appointment


def _login(client, username, password):
    client.post("/auth/login", data={"login": username, "password": password})


def test_admin_cannot_toggle_another_admin(client, admin_user, user_factory):
    other_admin = user_factory(username="admin2", role="admin")
    _login(client, "admin", "Admin@123")

    response = client.post(
        f"/admin/users/{other_admin.id}/toggle", follow_redirects=True
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "仅支持启用/禁用普通用户" in body
    db.session.refresh(other_admin)
    assert other_admin.is_active is True


def test_admin_user_list_does_not_offer_admin_operations(client, admin_user):
    _login(client, "admin", "Admin@123")
    body = client.get("/admin/users").get_data(as_text=True)
    assert "管理员账号由个人中心/CLI 维护" in body
    assert f"/admin/users/{admin_user.id}/reset-password" not in body
    assert f"/admin/users/{admin_user.id}/toggle" not in body


def test_offline_service_detail_is_hidden(client, service_factory):
    offline = service_factory(name="已下架详情", status="offline")
    response = client.get(f"/services/{offline.id}", follow_redirects=True)
    assert response.status_code == 200
    assert "该服务不存在或已下架" in response.get_data(as_text=True)


def test_user_cannot_cancel_confirmed_after_slot_started(
    app, normal_user, service, appointment_factory
):
    appointment = appointment_factory(normal_user, service, status="confirmed")
    started = datetime.combine(appointment.appointment_date, time(9, 30))

    ok, message = cancel_appointment(appointment, normal_user, now=started)
    assert ok is False
    assert "已开始" in message
    db.session.refresh(appointment)
    assert appointment.status == "confirmed"


def test_user_cannot_cancel_past_confirmed(
    app, normal_user, service, appointment_factory
):
    appointment = appointment_factory(
        normal_user,
        service,
        appointment_date=date.today() - timedelta(days=1),
        status="confirmed",
    )
    ok, message = cancel_appointment(appointment, normal_user)
    assert ok is False
    assert "已开始" in message
    db.session.refresh(appointment)
    assert appointment.status == "confirmed"


def test_admin_can_cancel_confirmed_after_slot_started(
    app, normal_user, admin_user, service, appointment_factory
):
    appointment = appointment_factory(normal_user, service, status="confirmed")
    started = datetime.combine(appointment.appointment_date, time(9, 30))

    ok, message = cancel_appointment(
        appointment, admin_user, is_admin=True, now=started
    )
    assert ok is True, message
    db.session.refresh(appointment)
    assert appointment.status == "cancelled"


def test_past_and_future_started_flags(app, normal_user, service, appointment_factory):
    past = appointment_factory(
        normal_user,
        service,
        appointment_date=date.today() - timedelta(days=1),
        status="confirmed",
    )
    future = appointment_factory(normal_user, service, status="confirmed")
    assert past.is_started is True
    assert future.is_started is False


def test_today_started_flag_uses_slot_time(
    monkeypatch, normal_user, service, appointment_factory
):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.combine(date.today(), time(10, 0))

    monkeypatch.setattr("app.models.appointment.datetime", FixedDateTime)
    started = appointment_factory(
        normal_user, service, appointment_date=date.today(), slot="09:00-10:00",
        status="confirmed",
    )
    later = appointment_factory(
        normal_user, service, appointment_date=date.today(), slot="14:00-15:00",
        status="confirmed",
    )
    assert started.is_started is True
    assert later.is_started is False


def test_past_confirmed_appointment_hides_cancel_button(
    client, normal_user, service, appointment_factory, monkeypatch
):
    appointment_factory(
        normal_user,
        service,
        appointment_date=date.today() - timedelta(days=1),
        status="confirmed",
    )
    # 关掉自动办结，让过去日期的记录保持 confirmed，专门验证模板是否隐藏取消按钮
    monkeypatch.setattr("app.modules.appointments.auto_complete_due", lambda **kwargs: 0)
    _login(client, "zhangsan", "User@123")
    body = client.get("/appointments/mine").get_data(as_text=True)
    assert "data-confirm=\"确定取消这条预约吗" not in body


def test_admin_consumer_pages_redirect_to_dashboard(client, admin_user):
    _login(client, "admin", "Admin@123")
    for path in ["/appointments/mine", "/feedback/mine", "/feedback/create"]:
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/admin/")


def test_user_admin_pages_are_forbidden(client, normal_user):
    _login(client, "zhangsan", "User@123")
    for path in ["/admin/", "/admin/users", "/admin/audit-logs"]:
        assert client.get(path).status_code == 403
