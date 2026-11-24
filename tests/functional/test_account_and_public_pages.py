"""用户交互功能测试：登录态页面、个人资料、公共页面与提示信息。

这些是实验四「用户交互的软件构造」的直接验收点：
  - 已登录用户再次访问登录/注册页应被引导回首页；
  - 个人资料修改成功/重邮箱冲突/非法手机号均有明确反馈；
  - 公告/服务详情不存在时给出提示并重定向，而不是 404 白屏或 500。
"""
from app.extensions import db
from app.models import User


def _login(client, username="zhangsan", password="User@123"):
    return client.post(
        "/auth/login", data={"login": username, "password": password}, follow_redirects=True
    )


def test_authenticated_user_is_redirected_away_from_login_and_register(client, normal_user):
    _login(client)
    assert client.get("/auth/login").status_code == 302
    assert client.get("/auth/register").status_code == 302
    assert client.get("/auth/login").headers["Location"].endswith("/")


def test_profile_update_success_keeps_own_email(client, normal_user):
    _login(client)
    response = client.post(
        "/auth/profile",
        data={
            "real_name": "张三丰",
            "email": normal_user.email.upper(),
            "phone": "13900139000",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "个人信息已更新" in response.get_data(as_text=True)
    refreshed = db.session.get(User, normal_user.id)
    assert refreshed.real_name == "张三丰"
    assert refreshed.email == normal_user.email  # 邮箱已小写，大小写变体视为本人
    assert refreshed.phone == "13900139000"


def test_profile_update_rejects_email_used_by_other(client, normal_user, admin_user):
    _login(client)
    response = client.post(
        "/auth/profile",
        data={"real_name": "张三", "email": admin_user.email, "phone": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "该邮箱已被其它账号使用" in response.get_data(as_text=True)
    assert db.session.get(User, normal_user.id).email == normal_user.email


def test_profile_update_to_new_email_succeeds(client, normal_user):
    _login(client)
    response = client.post(
        "/auth/profile",
        data={"real_name": "张三", "email": "new-address@example.com", "phone": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "个人信息已更新" in response.get_data(as_text=True)
    assert db.session.get(User, normal_user.id).email == "new-address@example.com"


def test_profile_update_rejects_invalid_phone(client, normal_user):
    _login(client)
    response = client.post(
        "/auth/profile",
        data={"real_name": "张三", "email": normal_user.email, "phone": "123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "手机号" in response.get_data(as_text=True)


def test_logout_clears_login_state(client, normal_user):
    _login(client)
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert "已安全退出登录" in response.get_data(as_text=True)
    assert client.get("/appointments/mine").status_code == 302


def test_favicon_and_about_pages(client):
    favicon = client.get("/favicon.ico")
    assert favicon.status_code == 302
    assert favicon.headers["Location"].endswith("favicon.svg")

    about = client.get("/about")
    assert about.status_code == 200


def test_announcement_no_match_and_missing_detail(client):
    response = client.get("/announcements/?keyword=不存在")
    assert response.status_code == 200
    assert "没有找到相关公告" in response.get_data(as_text=True)

    response = client.get("/announcements/99999", follow_redirects=True)
    assert response.status_code == 200
    assert "该公告不存在或未发布" in response.get_data(as_text=True)


def test_service_detail_missing_redirects_with_message(client):
    response = client.get("/services/99999", follow_redirects=True)
    assert response.status_code == 200
    assert "该服务不存在或已下架" in response.get_data(as_text=True)


def test_appointments_page_tolerates_invalid_status(client, normal_user):
    _login(client)
    response = client.get("/appointments/mine?status=not-a-status&page=0")
    assert response.status_code == 200


def test_feedback_page_without_reviewable_appointments(client, normal_user):
    _login(client)
    response = client.get("/feedback/create", follow_redirects=True)
    assert response.status_code == 200
    assert "没有可评价的预约" in response.get_data(as_text=True)
