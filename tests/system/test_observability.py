"""可观测性与安全响应测试：安全头、请求 ID、访问日志、禁用账号会话失效。"""
import logging

from app.extensions import db
from app.models import User
from app.repositories import UserRepository


def test_security_headers_are_present(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["X-XSS-Protection"] == "0"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    # 模板已去除内联样式，CSP 不应整体放开
    assert "unsafe-inline" not in csp


def test_request_id_is_generated_and_echoed(client):
    first = client.get("/")
    generated = first.headers["X-Request-ID"]
    assert len(generated) == 12

    second = client.get("/", headers={"X-Request-ID": "client-abc-123"})
    assert second.headers["X-Request-ID"] == "client-abc-123"


def test_request_id_rejects_oversized_value(client):
    response = client.get("/", headers={"X-Request-ID": "a" * 65})
    assert response.headers["X-Request-ID"] != "a" * 65
    assert len(response.headers["X-Request-ID"]) == 12


def test_access_log_contains_method_path_status(client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    response = client.get("/services/")
    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    assert any("GET /services/" in message and "200" in message for message in messages)


def test_static_requests_are_not_logged_as_page_views(client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    assert not any("GET /static" in message for message in messages)
    assert response.headers["X-Request-ID"]


def test_hsts_only_on_secure_requests_when_enabled(client, app):
    assert "Strict-Transport-Security" not in client.get("/").headers

    app.config["SESSION_COOKIE_SECURE"] = True
    response = client.get("/", base_url="https://localhost")
    assert response.headers["Strict-Transport-Security"].startswith("max-age=31536000")


def test_disabling_user_invalidates_existing_session(client, normal_user):
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    assert client.get("/appointments/mine").status_code == 200

    UserRepository.set_active(normal_user, False)
    assert db.session.get(User, normal_user.id).is_active is False

    response = client.get("/appointments/mine")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_malformed_session_user_id_is_treated_as_anonymous(client):
    with client.session_transaction() as session:
        session["_user_id"] = "not-an-int"
    response = client.get("/appointments/mine")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_missing_user_in_session_is_treated_as_anonymous(client):
    """会话中的用户 id 合法但记录已不存在（被删/迁移）时，必须回到登录页。"""
    with client.session_transaction() as session:
        session["_user_id"] = "99999"
    response = client.get("/appointments/mine")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_valid_user_in_session_is_loaded(client, normal_user):
    """正常路径：用户 id 有效且启用时，user_loader 必须返回用户对象。"""
    with client.session_transaction() as session:
        session["_user_id"] = str(normal_user.id)
    from flask import g

    g.pop("_login_user", None)
    response = client.get("/appointments/mine")
    assert response.status_code == 200


def test_deleted_user_session_is_treated_as_anonymous(client, user_factory):
    user = user_factory()
    client.post("/auth/login", data={"login": user.username, "password": "User@123"})
    assert client.get("/appointments/mine").status_code == 200

    db.session.delete(user)
    db.session.commit()
    # 测试夹具复用了同一个 app context，Flask-Login 会把 current_user 缓存在 g 上；
    # 清掉缓存以模拟真实服务器"每个请求独立 app context"的行为。
    from flask import g

    g.pop("_login_user", None)
    response = client.get("/appointments/mine")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


