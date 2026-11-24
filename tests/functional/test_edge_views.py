"""边界视图测试：缺失实体、表单 GET 页、非法评价与预约入口。

这些路径通常只在用户手输 URL、旧链接失效或并发删除时出现；
若没有统一兜底，就会从"可理解的提示"退化成 404/500。
"""
from app.extensions import db
from app.models import Appointment, Feedback


def _login(client, username="zhangsan", password="User@123"):
    return client.post(
        "/auth/login", data={"login": username, "password": password}, follow_redirects=True
    )


def _login_admin(client):
    return _login(client, "admin", "Admin@123")


def test_admin_form_pages_render(client, admin_user):
    _login_admin(client)
    assert client.get("/admin/services/new").status_code == 200
    assert client.get("/admin/announcements/new").status_code == 200


def test_admin_missing_user_toggle_shows_message(client, admin_user):
    _login_admin(client)
    response = client.post("/admin/users/99999/toggle", follow_redirects=True)
    assert response.status_code == 200
    assert "用户不存在" in response.get_data(as_text=True)


def test_admin_missing_appointment_status_shows_message(client, admin_user):
    _login_admin(client)
    response = client.post(
        "/admin/appointments/99999/status", data={"status": "confirmed"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert "预约不存在" in response.get_data(as_text=True)


def test_create_appointment_for_missing_service_redirects(client, normal_user):
    _login(client)
    response = client.get("/appointments/create/99999", follow_redirects=True)
    assert response.status_code == 200
    assert "该服务不存在或已下架" in response.get_data(as_text=True)


def test_cancel_missing_appointment_shows_message(client, normal_user):
    _login(client)
    response = client.post("/appointments/99999/cancel", follow_redirects=True)
    assert response.status_code == 200
    assert "预约记录不存在" in response.get_data(as_text=True)


def test_feedback_cannot_review_other_users_appointment(
    client, normal_user, user_factory, service_factory, appointment_factory
):
    other = user_factory()
    service = service_factory(name="他人的预约服务")
    appointment = appointment_factory(other, service, status="completed")
    _login(client)

    response = client.post(
        "/feedback/create",
        data={"appointment_id": str(appointment.id), "rating": "5", "content": "越权评价"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # 下拉选项只包含本人的可评价预约，因此非法 appointment_id 会在表单层被拒绝；
    # 无论走表单层还是服务层，都必须保证不写入评价（纵深防御）。
    assert db.session.query(Feedback).count() == 0
    assert db.session.get(Appointment, appointment.id).status == "completed"


def test_feedback_view_shows_service_layer_error(
    client, normal_user, service_factory, appointment_factory, monkeypatch
):
    """服务层返回失败时，视图必须把原因反馈给用户，而不是静默重定向。"""
    service = service_factory(name="服务层失败服务")
    appointment = appointment_factory(normal_user, service, status="completed")
    _login(client)

    monkeypatch.setattr(
        "app.modules.feedback.create_feedback",
        lambda *args, **kwargs: (None, "模拟服务层拒绝"),
    )
    response = client.post(
        "/feedback/create",
        data={"appointment_id": str(appointment.id), "rating": "5", "content": "内容"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "模拟服务层拒绝" in response.get_data(as_text=True)
