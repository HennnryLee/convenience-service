"""密码强度校验规则的单元测试（TDD：先写用例，再实现）。

被测单元：app.services.password_policy.validate_password
覆盖：长度边界（7/8/20/21 位）、字符类型、空格、与用户名相同。
"""
import pytest

from app.services.password_policy import validate_password


@pytest.mark.parametrize(
    "password,expect_ok",
    [
        ("Abc12345", True),        # 8 位（下边界）合法
        ("Abc1234", False),        # 7 位（下边界-1）非法
        ("Abcdefgh", False),       # 8 位但缺数字
        ("12345678", False),       # 8 位但缺字母
        ("A" * 19 + "1", True),    # 20 位（上边界）合法
        ("A" * 20 + "1", False),   # 21 位（上边界+1）非法
        ("Abc 1234", False),       # 含空格
        ("", False),               # 空密码
    ],
)
def test_password_length_and_composition(password, expect_ok):
    errors = validate_password(password)
    assert (len(errors) == 0) is expect_ok


def test_password_cannot_equal_username():
    errors = validate_password("zhangsan1", username="zhangsan1")
    assert any("不能与用户名相同" in e for e in errors)


def test_password_may_contain_special_chars():
    assert validate_password("Abc@12345") == []


def test_error_messages_are_specific():
    """错误信息应当逐条说明原因，便于前端逐项提示。"""
    errors = validate_password("abc")
    assert any("长度" in e for e in errors)
    assert any("字母" in e for e in errors)
    assert any("数字" in e for e in errors)
