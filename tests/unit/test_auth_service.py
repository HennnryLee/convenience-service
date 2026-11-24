"""用户管理服务单元测试：注册校验、登录认证、资料修改。"""
from app.models import User
from app.services import auth_service


def test_validate_registration_ok(app):
    errors = auth_service.validate_registration(
        "newuser", "new@example.com", "User@123", "User@123", phone="13800138000")
    assert errors == {}


def test_validate_registration_reports_each_field(app, normal_user):
    errors = auth_service.validate_registration(
        "zhangsan", "zhangsan@example.com", "123", "456", phone="123")
    assert "username" in errors and "已被注册" in errors["username"]
    assert "email" in errors and "已被注册" in errors["email"]
    assert "phone" in errors
    assert "password" in errors
    assert "confirm" in errors and "不一致" in errors["confirm"]


def test_validate_registration_rejects_bad_formats(app):
    errors = auth_service.validate_registration(
        "ab", "not-an-email", "Abcdefgh", "Abcdefgh", phone="12345"
    )
    assert "username" in errors
    assert "email" in errors
    assert "phone" in errors
    # 密码规则：8-20 位且同时含字母与数字
    assert "password" in errors


def test_validate_registration_allows_empty_optional_phone(app):
    errors = auth_service.validate_registration(
        "phoneuser", "phone@example.com", "User@123", "User@123", phone=""
    )
    assert errors == {}


def test_register_user_hashes_password(app):
    user = auth_service.register_user("user001", "u1@example.com", "User@123")
    assert User.query.filter_by(username="user001").first() is not None
    assert user.check_password("User@123") and not user.check_password("wrong")


def test_authenticate_success_and_failure(app, normal_user):
    assert auth_service.authenticate("zhangsan", "User@123") is not None
    assert auth_service.authenticate("zhangsan@example.com", "User@123") is not None  # 邮箱登录
    assert auth_service.authenticate("zhangsan", "Bad@1234") is None
    assert auth_service.authenticate("nobody", "User@123") is None
    assert auth_service.authenticate("", "") is None


def test_authenticate_disabled_user_still_authenticates_but_login_is_blocked(app, normal_user, client):
    """认证与授权分离：凭据正确即通过认证，是否启用由视图层给出明确提示。"""
    from app.repositories import UserRepository

    UserRepository.set_active(normal_user, False)
    assert auth_service.authenticate("zhangsan", "User@123") is normal_user

    # 登录页仍应拒绝，并提示账号被禁用（而不是笼统的"用户名或密码错误"）
    resp = client.post(
        "/auth/login",
        data={"login": "zhangsan", "password": "User@123"},
        follow_redirects=True,
    )
    assert "账号已被禁用".encode() in resp.data


def test_update_profile_and_validation(app, normal_user, admin_user):
    errors = auth_service.validate_profile("bad-email", "123")
    assert "email" in errors and "phone" in errors

    errors = auth_service.validate_profile("admin@example.com", "13900139000")
    assert "email" in errors  # 已被其它账号占用

    assert auth_service.validate_profile("ok@example.com", "13900139000") == {}
    auth_service.update_profile(normal_user, email="ok@example.com",
                                phone="13900139000", real_name="张三丰")
    assert normal_user.email == "ok@example.com"
    assert normal_user.phone == "13900139000"
    assert normal_user.real_name == "张三丰"


def test_feedback_rejects_invalid_rating(app, normal_user, service, appointment):
    from app.services.feedback_service import create_feedback

    appointment.status = "completed"
    for rating in (0, 6, 3.5, "5"):
        feedback, reason = create_feedback(normal_user, appointment, rating)
        assert feedback is None
        assert "评分" in reason


def test_feedback_rejects_missing_or_foreign_appointment(app, normal_user, admin_user):
    from app.services.feedback_service import create_feedback

    feedback, reason = create_feedback(normal_user, None, 5)
    assert feedback is None and "预约记录不存在" in reason

    foreign = type("Foreign", (), {"id": 999, "user_id": admin_user.id, "status": "completed"})()
    feedback, reason = create_feedback(normal_user, foreign, 5)
    assert feedback is None and "只能评价本人的预约" in reason
