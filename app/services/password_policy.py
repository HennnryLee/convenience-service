"""密码强度校验规则（用户管理模块的公共规则，纯函数，便于白盒覆盖测试）。

规则（与用户故事 US-01 验收标准一致）：
  R1 长度 8–20 位
  R2 必须同时包含字母和数字
  R3 不能包含空格
  R4 不能与用户名完全相同
"""
from app.config import Config

MIN_LENGTH = Config.PASSWORD_MIN_LENGTH   # 8
MAX_LENGTH = Config.PASSWORD_MAX_LENGTH   # 20


def validate_password(password, username=None):
    """校验密码强度。

    前置条件：password 为字符串（允许为空串）。
    后置条件：返回错误信息列表；为空表示密码合法。
    不变量：不修改入参，不抛异常。
    """
    errors = []
    if password is None:
        password = ""

    if not (MIN_LENGTH <= len(password) <= MAX_LENGTH):
        errors.append(f"密码长度必须为 {MIN_LENGTH}-{MAX_LENGTH} 位（当前 {len(password)} 位）。")

    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    if not (has_letter and has_digit):
        errors.append("密码必须同时包含字母和数字。")

    if any(ch.isspace() for ch in password):
        errors.append("密码不能包含空格。")

    if username and password == username:
        errors.append("密码不能与用户名相同。")

    return errors
