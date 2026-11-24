"""管理员后台重置普通用户密码（课程级找回密码）测试。

设计约定：
  - 管理员手动输入临时密码，不发送邮件；
  - 不强制下次登录改密，只在页面提示用户自行修改；
  - 仅允许重置普通用户，管理员账号走个人中心/CLI。
"""
from app.extensions import db
from app.models import AuditLog
from app.services.auth_service import reset_user_password


def _login_admin(client):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})


def _login_user(client):
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})


def test_admin_reset_password_success(client, admin_user, normal_user):
    _login_admin(client)
    page = client.get(f"/admin/users/{normal_user.id}/reset-password")
    assert page.status_code == 200
    assert normal_user.username in page.get_data(as_text=True)

    response = client.post(
        f"/admin/users/{normal_user.id}/reset-password",
        data={"password": "NewPass123", "confirm": "NewPass123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "密码已重置" in response.get_data(as_text=True)

    db.session.refresh(normal_user)
    assert normal_user.check_password("NewPass123") is True
    assert normal_user.check_password("User@123") is False

    log = db.session.query(AuditLog).filter_by(action="user.reset_password").one()
    assert log.target_id == normal_user.id
    assert "zhangsan" in log.detail
    assert log.action_text == "重置用户密码"


def test_admin_reset_rejects_weak_password(client, admin_user, normal_user):
    _login_admin(client)
    response = client.post(
        f"/admin/users/{normal_user.id}/reset-password",
        data={"password": "123", "confirm": "123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "密码" in response.get_data(as_text=True)
    db.session.refresh(normal_user)
    assert normal_user.check_password("User@123") is True
    assert db.session.query(AuditLog).filter_by(action="user.reset_password").count() == 0


def test_admin_reset_rejects_mismatched_confirm(client, admin_user, normal_user):
    _login_admin(client)
    response = client.post(
        f"/admin/users/{normal_user.id}/reset-password",
        data={"password": "NewPass123", "confirm": "OtherPass123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "两次输入的密码不一致" in response.get_data(as_text=True)
    db.session.refresh(normal_user)
    assert normal_user.check_password("User@123") is True


def test_admin_reset_only_for_regular_users(client, admin_user):
    _login_admin(client)
    response = client.get(
        f"/admin/users/{admin_user.id}/reset-password", follow_redirects=True
    )
    assert response.status_code == 200
    assert "仅支持重置普通用户" in response.get_data(as_text=True)


def test_reset_password_requires_admin(client, normal_user):
    _login_user(client)
    assert client.get(f"/admin/users/{normal_user.id}/reset-password").status_code == 403


def test_reset_password_requires_login(client, normal_user):
    response = client.get(f"/admin/users/{normal_user.id}/reset-password")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_reset_missing_user_redirects(client, admin_user):
    _login_admin(client)
    response = client.get("/admin/users/99999/reset-password", follow_redirects=True)
    assert response.status_code == 200
    assert "用户不存在" in response.get_data(as_text=True)


def test_reset_service_guards(app, admin_user, normal_user):
    ok, message = reset_user_password(None, "NewPass123")
    assert ok is False and "不存在" in message

    ok, message = reset_user_password(admin_user, "NewPass123")
    assert ok is False and "仅支持重置普通用户" in message

    ok, message = reset_user_password(normal_user, "123")
    assert ok is False and "密码" in message


def test_reset_route_shows_service_error(client, admin_user, normal_user, monkeypatch):
    _login_admin(client)
    monkeypatch.setattr(
        "app.modules.admin.auth_service.reset_user_password",
        lambda *args, **kwargs: (False, "模拟服务层拒绝"),
    )
    response = client.post(
        f"/admin/users/{normal_user.id}/reset-password",
        data={"password": "NewPass123", "confirm": "NewPass123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "模拟服务层拒绝" in response.get_data(as_text=True)
