"""用户交互集成测试：验证页面跳转、表单提交、会话管理与权限控制。

被测层次：蓝图视图 + 表单校验 + Flask-Login 会话 + 数据库写入的协同。
"""
from datetime import date, timedelta

from app.extensions import db
from app.models import Appointment, ServiceItem, User


# ------------------------------------------------------------------ 注册
def test_register_success_writes_user(client):
    resp = client.post(
        "/auth/register",
        data={
            "username": "lisi",
            "email": "lisi@example.com",
            "phone": "13900139000",
            "real_name": "李四",
            "password": "User@123",
            "confirm": "User@123",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert User.query.filter_by(username="lisi").first() is not None


def test_register_duplicate_username_rejected(client, normal_user):
    resp = client.post(
        "/auth/register",
        data={"username": "zhangsan", "email": "other@example.com",
              "password": "User@123", "confirm": "User@123"},
        follow_redirects=True,
    )
    assert b"\xe8\xaf\xa5\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe5\xb7\xb2\xe8\xa2\xab\xe6\xb3\xa8\xe5\x86\x8c" in resp.data \
        or "该用户名已被注册".encode() in resp.data
    assert User.query.filter_by(email="other@example.com").first() is None


def test_register_weak_password_rejected(client):
    resp = client.post(
        "/auth/register",
        data={"username": "wangwu", "email": "ww@example.com",
              "password": "123", "confirm": "123"},
    )
    assert resp.status_code == 200
    assert User.query.filter_by(username="wangwu").first() is None


# ------------------------------------------------------------------ 登录 / 会话
def test_login_success_and_session_kept(client, normal_user):
    resp = client.post(
        "/auth/login", data={"login": "zhangsan", "password": "User@123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "欢迎回来".encode() in resp.data
    # 会话保持：可访问需要登录的页面
    assert client.get("/appointments/mine").status_code == 200


def test_login_wrong_password(client, normal_user):
    resp = client.post(
        "/auth/login", data={"login": "zhangsan", "password": "Wrong@123"},
        follow_redirects=True,
    )
    assert "用户名或密码错误".encode() in resp.data


def test_logout_clears_session(client, normal_user):
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    client.get("/auth/logout", follow_redirects=True)
    assert client.get("/appointments/mine").status_code == 302  # 退出后需重新登录


# ------------------------------------------------------------------ 访问控制
def test_anonymous_redirected_to_login(client):
    resp = client.get("/appointments/mine")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_normal_user_cannot_access_admin(client, normal_user):
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    assert client.get("/admin/").status_code == 403


def test_admin_can_access_admin(client, admin_user):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/services").status_code == 200
    assert client.get("/admin/users").status_code == 200
    assert client.get("/admin/appointments").status_code == 200


# ------------------------------------------------------------------ 预约表单
def _login(client):
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})


def test_appointment_form_submit_success(client, normal_user, service):
    _login(client)
    day = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
    resp = client.post(
        f"/appointments/create/{service.id}",
        data={
            "appointment_date": day,
            "time_slot": "09:00-10:00",
            "contact_name": "张三",
            "contact_phone": "13800138000",
            "remark": "希望上午办理",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "预约提交成功".encode() in resp.data
    assert Appointment.query.filter_by(user_id=normal_user.id).count() == 1


def test_appointment_invalid_phone_shows_error_and_no_write(client, normal_user, service):
    _login(client)
    day = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
    resp = client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": day, "time_slot": "09:00-10:00",
              "contact_name": "张三", "contact_phone": "123"},
    )
    assert resp.status_code == 200
    assert "手机号格式不正确".encode() in resp.data or "联系电话".encode() in resp.data
    assert Appointment.query.count() == 0


def test_appointment_requires_login(client, service):
    resp = client.get(f"/appointments/create/{service.id}")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_cancel_appointment_flow(client, normal_user, service, appointment):
    _login(client)
    resp = client.post(f"/appointments/{appointment.id}/cancel", follow_redirects=True)
    assert resp.status_code == 200
    assert "预约已取消".encode() in resp.data
    assert Appointment.query.get(appointment.id).status == "cancelled"


# ------------------------------------------------------------------ 服务与公告页面
def test_service_list_and_detail_pages(client, service):
    resp = client.get("/services/")
    assert resp.status_code == 200
    assert service.name.encode() in resp.data

    resp = client.get(f"/services/{service.id}")
    assert resp.status_code == 200
    assert "今日各时段剩余名额".encode() in resp.data


def test_service_search_with_keyword(client, service):
    resp = client.get("/services/?keyword=" + "身份证")
    assert resp.status_code == 200
    assert service.name.encode() in resp.data
    assert client.get("/services/?keyword=" + "不存在").status_code == 200


def test_announcement_pages(client, announcement):
    resp = client.get("/announcements/")
    assert resp.status_code == 200 and announcement.title.encode() in resp.data
    resp = client.get(f"/announcements/{announcement.id}")
    assert resp.status_code == 200 and announcement.content[:10].encode() in resp.data


# ------------------------------------------------------------------ 后台管理
def test_admin_create_service(client, admin_user):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})
    resp = client.post(
        "/admin/services/new",
        data={"name": "新生儿户口登记咨询", "category": "government",
              "description": "新生儿落户材料与流程咨询。", "address": "市民之家 A 区 6 号窗口",
              "price": "0", "duration_minutes": "30", "daily_capacity": "4", "status": "online"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert ServiceItem.query.filter_by(name="新生儿户口登记咨询").first() is not None


def test_admin_toggle_service_status(client, admin_user, service):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})
    resp = client.post(f"/admin/services/{service.id}/toggle", follow_redirects=True)
    assert resp.status_code == 200
    assert ServiceItem.query.get(service.id).status == "offline"
    # 下架后前台查询不到
    assert service.name.encode() not in client.get("/services/").data


def test_admin_change_appointment_status(client, admin_user, service, appointment):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})
    resp = client.post(
        f"/admin/appointments/{appointment.id}/status",
        data={"status": "confirmed"}, follow_redirects=True)
    assert resp.status_code == 200
    assert Appointment.query.get(appointment.id).status == "confirmed"


def test_admin_can_publish_announcement(client, admin_user):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})
    resp = client.post(
        "/admin/announcements/new",
        data={"title": "国庆假期服务安排", "content": "10 月 1 日至 7 日部分窗口暂停服务。",
              "is_published": "y"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "国庆假期服务安排".encode() in client.get("/announcements/").data
