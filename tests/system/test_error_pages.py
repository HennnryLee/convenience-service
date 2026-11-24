"""统一错误页测试（400 / 403 / 404 / 405 / 413 / 500）。

覆盖 `app/errors.py`：错误码、页面文案、5xx 不泄露堆栈、CSRF 失败提示。
"""
from app.extensions import db
from flask import abort


def _login(client, username="zhangsan", password="User@123"):
    return client.post(
        "/auth/login", data={"login": username, "password": password}, follow_redirects=True
    )


def test_404_renders_unified_page(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert "页面不存在" in response.get_data(as_text=True)
    assert "返回首页" in response.get_data(as_text=True)


def test_405_for_method_not_allowed(client):
    response = client.post("/", data={})
    assert response.status_code == 405
    assert "请求方法不允许" in response.get_data(as_text=True)


def test_403_for_normal_user_accessing_admin(client, normal_user):
    _login(client)
    response = client.get("/admin/")
    assert response.status_code == 403
    assert "无访问权限" in response.get_data(as_text=True)


def test_400_bad_request_handler(client, app):
    @app.route("/__bad-request")
    def bad_request():
        abort(400)

    response = client.get("/__bad-request")
    assert response.status_code == 400
    assert "请求无法处理" in response.get_data(as_text=True)


def test_413_request_too_large(client):
    response = client.post(
        "/auth/login",
        data=b"x" * (1024 * 1024 + 1),
        content_type="application/x-www-form-urlencoded",
    )
    assert response.status_code == 413
    assert "请求内容过大" in response.get_data(as_text=True)


def test_500_logs_and_hides_internal_detail(client, app, caplog):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/__boom")
    def boom():
        raise RuntimeError("secret-detail-should-not-leak")

    response = client.get("/__boom")
    text = response.get_data(as_text=True)
    assert response.status_code == 500
    assert "服务器内部错误" in text
    assert "secret-detail-should-not-leak" not in text
    assert "secret-detail-should-not-leak" in caplog.text


def test_csrf_failure_returns_400_page(client, app):
    """测试环境默认关闭 CSRF；本用例显式打开，验证真实部署下的失败页面。"""
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post(
        "/auth/login", data={"login": "zhangsan", "password": "User@123"}
    )
    assert response.status_code == 400
    assert "表单已过期或校验失败" in response.get_data(as_text=True)


def test_database_still_usable_after_error_pages(client, normal_user):
    assert client.get("/no-such-page").status_code == 404
    assert db.session.get(type(normal_user), normal_user.id) is normal_user
