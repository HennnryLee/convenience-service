"""用户管理服务：注册、登录、资料修改（业务编排层）。

依赖：UserRepository（数据访问）+ password_policy / validators（规则）
依赖方向：单向向下，数据层不反向调用本模块。
"""
from app.repositories.user_repository import UserRepository
from app.services.password_policy import validate_password
from app.utils.validators import is_valid_email, is_valid_phone, is_valid_username


def validate_registration(username, email, password, confirm, phone=None):
    """注册信息校验。

    后置条件：返回 {字段名: 错误信息} 字典；空字典表示校验通过。
    """
    errors = {}

    if not is_valid_username(username):
        errors["username"] = "用户名需为 3-20 位字母、数字或下划线。"
    elif UserRepository.username_exists(username):
        errors["username"] = "该用户名已被注册。"

    if not is_valid_email(email):
        errors["email"] = "邮箱格式不正确。"
    elif UserRepository.email_exists(email):
        errors["email"] = "该邮箱已被注册。"

    if phone and not is_valid_phone(phone):
        errors["phone"] = "手机号需为 11 位有效号码。"

    password_errors = validate_password(password, username=username)
    if password_errors:
        errors["password"] = "；".join(password_errors)

    if password != confirm:
        errors["confirm"] = "两次输入的密码不一致。"

    return errors


def register_user(username, email, password, phone=None, real_name=None, role="user"):
    """注册新用户。前置条件：已通过 validate_registration 校验。"""
    return UserRepository.create(
        username=username,
        email=email,
        password=password,
        phone=phone,
        real_name=real_name,
        role=role,
    )


def authenticate(login, password):
    """校验登录凭据。

    后置条件：用户名/邮箱存在且密码匹配时返回 User，否则返回 None。
    注意：本函数只做**身份认证**，不判断账号是否启用；
    "禁用账号"属于授权策略，由视图层在认证通过后给出明确提示，
    这样既不会向攻击者泄露账号是否存在，也能让真实用户知道该联系管理员。
    安全考虑：无论用户不存在还是密码错误，对外统一提示，避免账号枚举。
    """
    user = UserRepository.get_by_login(login)
    if user is None or not user.check_password(password):
        return None
    return user


def validate_profile(email, phone):
    errors = {}
    if not is_valid_email(email):
        errors["email"] = "邮箱格式不正确。"
    elif UserRepository.email_exists(email):
        errors["email"] = "该邮箱已被其它账号使用。"
    if phone and not is_valid_phone(phone):
        errors["phone"] = "手机号需为 11 位有效号码。"
    return errors


def update_profile(user, email=None, phone=None, real_name=None):
    return UserRepository.update(
        user, email=email, phone=phone, real_name=real_name
    )
