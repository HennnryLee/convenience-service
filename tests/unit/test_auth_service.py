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


def test_authenticate_disabled_user_rejected(app, normal_user):
    from app.repositories import UserRepository

    UserRepository.set_active(normal_user, False)
    assert auth_service.authenticate("zhangsan", "User@123") is None


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
