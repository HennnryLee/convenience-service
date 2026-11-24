"""后台服务管理的功能测试：新建/编辑/重名/分页与筛选边界。

重点回归：编辑服务改名撞库原本会触发数据库唯一约束并返回 500，
现在必须在保存前给出"同名服务已存在"的可理解提示。
"""
from app.extensions import db
from app.models import ServiceItem


def _login_admin(client):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})


def _service_form_data(name, **overrides):
    data = {
        "name": name,
        "category": "life",
        "description": "测试服务简介",
        "address": "测试地址",
        "price": "12.5",
        "duration_minutes": "30",
        "daily_capacity": "4",
        "status": "online",
    }
    data.update(overrides)
    return data


def test_admin_creates_service(client, admin_user):
    _login_admin(client)
    response = client.post(
        "/admin/services/new", data=_service_form_data("新服务"), follow_redirects=True
    )
    assert response.status_code == 200
    assert "服务已创建" in response.get_data(as_text=True)
    assert db.session.query(ServiceItem).filter_by(name="新服务").count() == 1


def test_admin_create_duplicate_name_is_rejected(client, admin_user, service_factory):
    service_factory(name="已存在服务")
    _login_admin(client)
    response = client.post(
        "/admin/services/new",
        data=_service_form_data("  已存在服务  "),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "同名服务已存在" in response.get_data(as_text=True)
    assert db.session.query(ServiceItem).filter_by(name="已存在服务").count() == 1


def test_admin_edit_to_duplicate_name_is_rejected_without_500(
    client, admin_user, service_factory
):
    first = service_factory(name="第一个服务")
    service_factory(name="第二个服务")
    _login_admin(client)

    response = client.post(
        f"/admin/services/{first.id}/edit",
        data=_service_form_data("第二个服务"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "同名服务已存在" in response.get_data(as_text=True)
    refreshed = db.session.get(ServiceItem, first.id)
    assert refreshed.name == "第一个服务"


def test_admin_edit_keeps_own_name(client, admin_user, service_factory):
    service = service_factory(name="保持原名")
    _login_admin(client)
    response = client.post(
        f"/admin/services/{service.id}/edit",
        data=_service_form_data("保持原名", price="99"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "服务信息已更新" in response.get_data(as_text=True)
    assert str(db.session.get(ServiceItem, service.id).price) in {"99.00", "99"}


def test_admin_edit_missing_service_redirects(client, admin_user):
    _login_admin(client)
    response = client.get("/admin/services/99999/edit", follow_redirects=True)
    assert response.status_code == 200
    assert "服务不存在" in response.get_data(as_text=True)


def test_admin_toggle_missing_service_redirects(client, admin_user):
    _login_admin(client)
    response = client.post("/admin/services/99999/toggle", follow_redirects=True)
    assert response.status_code == 200
    assert "服务不存在" in response.get_data(as_text=True)


def test_admin_lists_tolerate_invalid_page_and_status(client, admin_user, service_factory):
    service_factory(name="列表服务")
    _login_admin(client)

    for url in (
        "/admin/services?page=0",
        "/admin/services?page=abc",
        "/admin/users?page=-1",
        "/admin/appointments?status=not-a-status&page=0",
        "/admin/feedbacks?page=abc",
    ):
        response = client.get(url)
        assert response.status_code == 200, url

    response = client.get("/admin/appointments?status=not-a-status")
    assert response.status_code == 200


def test_admin_cannot_disable_self(client, admin_user):
    _login_admin(client)
    response = client.post(f"/admin/users/{admin_user.id}/toggle", follow_redirects=True)
    assert response.status_code == 200
    assert "不能禁用当前登录的管理员账号" in response.get_data(as_text=True)
    assert db.session.get(type(admin_user), admin_user.id).is_active is True
