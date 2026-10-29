"""通用格式校验（纯函数，便于单元测试与复用）。

与业务规则分离：本模块只回答"格式是否合法"，不回答"业务是否允许"。
"""
import re

PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def is_valid_phone(phone):
    """中国大陆 11 位手机号。"""
    return bool(phone) and bool(PHONE_PATTERN.match(phone))


def is_valid_email(email):
    return bool(email) and bool(EMAIL_PATTERN.match(email))


def is_valid_username(username):
    """3–20 位字母、数字或下划线。"""
    return bool(username) and bool(USERNAME_PATTERN.match(username))


def validate_keyword(keyword, max_length=50):
    """搜索关键词校验：允许为空（视为不过滤），超出长度上限则报错。"""
    if keyword is None:
        return ""
    keyword = keyword.strip()
    if len(keyword) > max_length:
        return None
    return keyword
