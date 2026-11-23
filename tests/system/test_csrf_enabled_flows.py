"""CSRF 开启环境下的端到端回归测试（软件测试实验四补充）。

缺陷背景
--------
TestingConfig 关闭了 ``WTF_CSRF_ENABLED``，因此所有"不带令牌直接 POST"的
用例在自动化测试中都能通过，导致「行内手写 POST 表单缺少 csrf_token」这一
缺陷完全无法暴露。而真实运行环境（DevelopmentConfig / ProductionConfig）
开启 CSRF 后，全局 CSRFProtect 会拦截这类表单并返回
``400 Bad Request: The CSRF token is missing.``。

本模块使用 development 配置 + 独立临时 SQLite 库，模拟真实浏览器
「先从页面渲染取令牌，再提交表单」的完整流程，覆盖 4 个行内表单：

  1. 后台预约管理 · 状态更新
  2. 后台服务管理 · 上架/下架
  3. 后台用户管理 · 启用/禁用
  4. 前台我的预约 · 取消预约

同时验证「缺失令牌仍被拒绝」，确保修复没有绕过安全防护。
"""
import re
from datetime import date, timedelta

import pytest

from app import create_app
from app.config import DevelopmentConfig
from app.extensions import db
from app.models import Appointment, ServiceItem, User

CSRF_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')


def get_token(html):
    """从页面 HTML 中提取 CSRF 令牌。"""
    match = CSRF_RE.search(html)
    assert match, "页面未渲染 csrf_token 隐藏字段"
    return match.group(1)


def login(client, username, password):
    """以真实登录表单（含令牌）登录。"""
    html = client.get("/auth/login").get_data(as_text=True)
    token = get_token(html)
    return client.post(
        "/auth/login",
        data={"csrf_token": token, "login": username, "password": password},
    )


@pytest.fixture()
def csrf_app(monkeypatch, tmp_path):
    """独立应用：development 配置（CSRF 开启）+ 临时文件数据库。

    通过 monkeypatch 修改配置类的类属性（而非实例 config），因为
    Flask-SQLAlchemy 在 db.init_app() 时即按类属性创建了引擎，
    之后再改 app.config 不会生效。使用临时文件库可确保完全不触碰
    用户真实的 instance/app.db。
    """
    db_file = tmp_path / "csrf_test.db"
    monkeypatch.setattr(
        DevelopmentConfig,
        "SQLALCHEMY_DATABASE_URI",
        "sqlite:///" + str(db_file).replace("\\", "/"),
    )
    app = create_app("development")
    app.config["WTF_CSRF_ENABLED"] = True

    with app.app_context():
        db.create_all()
        admin = User(username="admin", email="admin@example.com", role="admin")
        admin.set_password("Admin@123")
        normal = User(username="lihang", email="lihang@example.com", role="user")
        normal.set_password("User@123")
        service = ServiceItem(
            name="社区洗衣干洗",
            category="life",
            description="衣物干洗、水洗与熨烫服务。",
            address="社区服务中心 1 层",
            price=25.00,
            duration_minutes=40,
            daily_capacity=5,
            status="online",
        )
        db.session.add_all([admin, normal, service])
        db.session.commit()

        appt = Appointment(
            user_id=normal.id,
            service_id=service.id,
            appointment_date=date.today() + timedelta(days=1),
            time_slot="09:00-10:00",
            contact_name="李行",
            contact_phone="13800138000",
            status="pending",
        )
        db.session.add(appt)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def test_missing_csrf_token_is_still_rejected(csrf_app):
    """防护本身有效：不带令牌的 POST 应被拒绝（400），修复不能绕过安全校验。"""
    client = csrf_app.test_client()
    login(client, "admin", "Admin@123")
    resp = client.post("/admin/appointments/1/status", data={"status": "confirmed"})
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "path, username, password",
    [
        ("/admin/appointments", "admin", "Admin@123"),
        ("/admin/services", "admin", "Admin@123"),
        ("/admin/users", "admin", "Admin@123"),
        ("/appointments/mine", "lihang", "User@123"),
    ],
)
def test_inline_forms_render_csrf_token(csrf_app, path, username, password):
    """4 个含行内 POST 表单的页面都必须渲染 csrf_token 隐藏字段。"""
    client = csrf_app.test_client()
    login(client, username, password)
    html = client.get(path).get_data(as_text=True)
    assert 'name="csrf_token"' in html, f"{path} 缺少 CSRF 令牌"


def test_admin_can_update_appointment_status(csrf_app):
    """复现用户报告的场景：管理员在预约管理页改状态并点「更新」。"""
    client = csrf_app.test_client()
    login(client, "admin", "Admin@123")

    html = client.get("/admin/appointments").get_data(as_text=True)
    token = get_token(html)
    resp = client.post(
        "/admin/appointments/1/status",
        data={"csrf_token": token, "status": "confirmed"},
    )
    assert resp.status_code == 302, resp.get_data(as_text=True)[:200]
    with csrf_app.app_context():
        assert Appointment.query.get(1).status == "confirmed"


def test_admin_can_toggle_service(csrf_app):
    """服务上架/下架行内表单可正常提交。"""
    client = csrf_app.test_client()
    login(client, "admin", "Admin@123")

    token = get_token(client.get("/admin/services").get_data(as_text=True))
    resp = client.post("/admin/services/1/toggle", data={"csrf_token": token})
    assert resp.status_code == 302
    with csrf_app.app_context():
        assert ServiceItem.query.get(1).status == "offline"


def test_admin_can_toggle_user(csrf_app):
    """用户启用/禁用行内表单可正常提交（不能禁用当前管理员，故操作普通用户）。"""
    client = csrf_app.test_client()
    login(client, "admin", "Admin@123")

    token = get_token(client.get("/admin/users").get_data(as_text=True))
    resp = client.post("/admin/users/2/toggle", data={"csrf_token": token})
    assert resp.status_code == 302
    with csrf_app.app_context():
        assert User.query.get(2).is_active is False


def test_user_can_cancel_appointment(csrf_app):
    """前台「取消预约」行内表单可正常提交。"""
    client = csrf_app.test_client()
    login(client, "lihang", "User@123")

    token = get_token(client.get("/appointments/mine").get_data(as_text=True))
    resp = client.post("/appointments/1/cancel", data={"csrf_token": token})
    assert resp.status_code == 302
    with csrf_app.app_context():
        assert Appointment.query.get(1).status == "cancelled"
