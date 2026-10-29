"""黑盒测试 · 等价类划分：用户注册功能。

被测：POST /auth/register
划分对象：用户名、密码、确认密码、邮箱、手机号。
每个等价类取一个代表值，验证"是否写入数据库"与"页面提示"两项结果。
"""
import pytest

from app.models import User


def post_register(client, **overrides):
    data = {
        "username": "equser01",
        "email": "eq@example.com",
        "phone": "13800138000",
        "real_name": "等价类用户",
        "password": "User@123",
        "confirm": "User@123",
    }
    data.update(overrides)
    return client.post("/auth/register", data=data, follow_redirects=True)


@pytest.mark.parametrize(
    "field,value,note",
    [
        # ---------------- 用户名 ----------------
        ("username", "ab", "无效等价类：2 位（下边界-1）"),
        ("username", "a" * 21, "无效等价类：21 位（上边界+1）"),
        ("username", "user name", "无效等价类：含空格"),
        ("username", "用户名字", "无效等价类：含中文"),
        ("email", "not-an-email", "无效等价类：邮箱缺少 @"),
        ("email", "a@b", "无效等价类：邮箱域名不完整"),
        ("phone", "1380013800", "无效等价类：手机号 10 位"),
        ("phone", "12345678901", "无效等价类：手机号非 1 开头"),
        ("phone", "abcdefghijk", "无效等价类：手机号非数字"),
        ("password", "Short1", "无效等价类：密码 6 位（<8）"),
        ("password", "NoDigitsHere", "无效等价类：密码缺数字"),
        ("password", "12345678", "无效等价类：密码缺字母"),
        ("password", "Pass 1234", "无效等价类：密码含空格"),
    ],
)
def test_invalid_equivalence_classes_rejected(client, field, value, note):
    """无效等价类：一律拒绝注册，且不写入数据库。"""
    resp = post_register(client, **{field: value})
    assert resp.status_code == 200
    assert User.query.count() == 0, f"{note} 不应写入数据库"


@pytest.mark.parametrize(
    "overrides,note",
    [
        ({"username": "equser01", "password": "User@123", "confirm": "User@123"}, "有效等价类：全部合法"),
        ({"username": "abc"}, "有效等价类：用户名 3 位（下边界）"),
        ({"username": "a" * 20}, "有效等价类：用户名 20 位（上边界）"),
        ({"phone": ""}, "有效等价类：手机号留空（选填项）"),
        ({"real_name": ""}, "有效等价类：真实姓名留空（选填项）"),
        ({"password": "Abc@12345", "confirm": "Abc@12345"}, "有效等价类：含特殊字符的强密码"),
    ],
)
def test_valid_equivalence_classes_accepted(client, overrides, note):
    """有效等价类：注册成功并写入数据库。"""
    resp = post_register(client, **overrides)
    assert resp.status_code == 200
    assert User.query.count() == 1, f"{note} 应写入数据库"
    assert "注册成功".encode() in resp.data


def test_password_confirm_mismatch_is_rejected(client):
    resp = post_register(client, confirm="User@124")
    assert "两次输入的密码不一致".encode() in resp.data
    assert User.query.count() == 0


def test_password_same_as_username_rejected(client):
    resp = post_register(client, username="User12345", password="User12345", confirm="User12345")
    assert "不能与用户名相同".encode() in resp.data
    assert User.query.count() == 0


def test_duplicate_username_and_email_rejected(client, normal_user):
    resp = post_register(client, username="zhangsan", email="new@example.com")
    assert "该用户名已被注册".encode() in resp.data
    resp = post_register(client, username="other01", email="zhangsan@example.com")
    assert "该邮箱已被注册".encode() in resp.data
    assert User.query.count() == 1  # 仅原有的 zhangsan


def test_empty_form_rejected(client):
    resp = client.post("/auth/register", data={}, follow_redirects=True)
    assert resp.status_code == 200
    assert User.query.count() == 0
