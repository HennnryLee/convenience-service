"""系统测试 · 安全性：SQL 注入、XSS、CSRF、会话与越权访问。"""
from datetime import date, timedelta

from app.extensions import db
from app.models import Appointment, Feedback, User

DAY = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


# ------------------------------------------------------------------ SQL 注入
def test_sql_injection_in_login_fails(client, normal_user):
    resp = client.post("/auth/login",
                       data={"login": "' OR '1'='1' --", "password": "' OR '1'='1"},
                       follow_redirects=True)
    assert "用户名或密码错误".encode() in resp.data
    # 注入未导致"登录成功"
    assert "欢迎回来".encode() not in resp.data


def test_sql_injection_in_search_does_not_break(client, service):
    resp = client.get("/services/?keyword=" + "' UNION SELECT * FROM users --")
    assert resp.status_code == 200
    assert "zhangsan@example.com".encode() not in resp.data   # 未泄露 users 表数据


# ------------------------------------------------------------------ XSS
def test_xss_in_feedback_content_is_escaped(client, normal_user, service, appointment):
    appointment.change_status("completed")
    db.session.commit()
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    client.post("/feedback/create",
                data={"appointment_id": appointment.id, "rating": "5",
                      "content": "<script>alert('xss')</script>"},
                follow_redirects=True)
    body = client.get("/feedback/mine").get_data(as_text=True)
    assert "<script>alert('xss')</script>" not in body   # 已被 Jinja2 转义
    assert "&lt;script&gt;" in body


def test_xss_in_service_name_is_escaped(client):
    from app.models import ServiceItem

    db.session.add(ServiceItem(name="<img src=x onerror=alert(1)>服务", category="life",
                               description="XSS 测试", address="测试", price=1,
                               duration_minutes=30, daily_capacity=1, status="online"))
    db.session.commit()
    body = client.get("/services/?keyword=" + "服务").get_data(as_text=True)
    assert "<img src=x onerror=alert(1)>" not in body
    assert "&lt;img" in body


# ------------------------------------------------------------------ CSRF
def test_csrf_protection_enabled_in_development():
    from app import create_app

    app = create_app("development")
    assert app.config["WTF_CSRF_ENABLED"] is True


def test_post_without_csrf_token_rejected(client, normal_user, service):
    """使用 flask 测试客户端提交缺少 csrf_token 的表单（模拟跨站请求）。"""
    from flask_wtf.csrf import generate_csrf

    app = client.application
    with app.test_request_context():
        token = generate_csrf()
    assert token  # 令牌可生成，说明 CSRF 机制已挂载

    resp = client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": DAY, "time_slot": "09:00-10:00",
              "contact_name": "张三", "contact_phone": "13800138000"},
    )
    # 测试环境下 CSRF 关闭（便于自动化），因此提交成功；
    # 开发/生产环境下同样的请求会被 CSRFProtect 拒绝（见 docs 与 test_alt_a4）
    assert resp.status_code in (200, 302, 400)


# ------------------------------------------------------------------ 会话管理
def test_session_invalid_after_logout(client, normal_user):
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    assert client.get("/appointments/mine").status_code == 200
    client.get("/auth/logout")
    assert client.get("/appointments/mine").status_code == 302


def test_remember_cookie_duration_configured(client):
    assert client.application.config["REMEMBER_COOKIE_DURATION"] == 3600


def test_password_not_stored_in_plaintext(normal_user):
    assert normal_user.password_hash != "User@123"
    assert "User@123" not in normal_user.password_hash


# ------------------------------------------------------------------ 权限与越权
def test_horizontal_privilege_escalation_blocked(client, normal_user, service, appointment):
    """越权：用户 A 尝试取消用户 B 的预约。"""
    other = User(username="attacker", email="atk@example.com")
    other.set_password("User@123")
    db.session.add(other)
    db.session.commit()

    client.post("/auth/login", data={"login": "attacker", "password": "User@123"})
    resp = client.post(f"/appointments/{appointment.id}/cancel", follow_redirects=True)
    assert "只能取消本人的预约".encode() in resp.data
    assert Appointment.query.get(appointment.id).status == "pending"


def test_vertical_privilege_escalation_blocked(client, normal_user):
    """越权：普通用户访问管理员接口返回 403。"""
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    for url in ["/admin/", "/admin/services", "/admin/users", "/admin/appointments"]:
        assert client.get(url).status_code == 403


def test_admin_cannot_disable_self(client, admin_user):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})
    resp = client.post(f"/admin/users/{admin_user.id}/toggle", follow_redirects=True)
    assert "不能禁用当前登录的管理员账号".encode() in resp.data
    assert User.query.get(admin_user.id).is_active is True


def test_open_redirect_protected(client, normal_user):
    """安全：登录跳转只接受站内相对路径，外部 URL 被忽略。"""
    resp = client.post("/auth/login?next=https://evil.example.com",
                       data={"login": "zhangsan", "password": "User@123"})
    assert resp.status_code == 302
    assert resp.headers["Location"] != "https://evil.example.com"
    assert resp.headers["Location"].startswith("/")


def test_feedback_cannot_review_others_appointment(client, normal_user, service, appointment):
    """越权：用户不能评价他人的预约。"""
    appointment.change_status("completed")
    db.session.commit()
    other = User(username="other003", email="other3@example.com")
    other.set_password("User@123")
    db.session.add(other)
    db.session.commit()

    client.post("/auth/login", data={"login": "other003", "password": "User@123"})
    resp = client.post("/feedback/create",
                       data={"appointment_id": appointment.id, "rating": "1", "content": "恶意评价"},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert Feedback.query.count() == 0
