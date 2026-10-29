"""黑盒测试 · 场景法：在线预约功能。

基本流：登录 → 进入服务详情 → 选择日期时段 → 填写联系信息 → 提交成功 → 出现在"我的预约"
备选流：
  A1 未登录访问预约页面（跳转登录页）
  A2 预约信息不完整/格式错误（逐项提示，不写库）
  A3 预约时段名额已满（提示已满，不写库）
  A4 提交时缺少 CSRF 令牌 / 会话失效（请求被拒绝，不写库）
"""
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Appointment, ServiceItem, User


TARGET_DAY = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


def _login(client):
    return client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"},
                       follow_redirects=True)


# ------------------------------------------------------------------ 基本流
def test_basic_flow_success(client, normal_user, service):
    _login(client)
    resp = client.get(f"/appointments/create/{service.id}")
    assert resp.status_code == 200

    resp = client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": TARGET_DAY, "time_slot": "09:00-10:00",
              "contact_name": "张三", "contact_phone": "13800138000", "remark": "基本流"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "预约提交成功".encode() in resp.data
    assert Appointment.query.filter_by(user_id=normal_user.id).count() == 1

    mine = client.get("/appointments/mine")
    assert "09:00-10:00".encode() in mine.data


# ------------------------------------------------------------------ 备选流
def test_alt_a1_anonymous_redirected_to_login(client, service):
    resp = client.get(f"/appointments/create/{service.id}")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
    assert Appointment.query.count() == 0


@pytest.mark.parametrize(
    "payload,expect_tip",
    [
        ({"appointment_date": "", "time_slot": "09:00-10:00",
          "contact_name": "张三", "contact_phone": "13800138000"}, "请选择预约日期"),
        ({"appointment_date": TARGET_DAY, "time_slot": "",
          "contact_name": "张三", "contact_phone": "13800138000"}, "请选择预约时段"),
        ({"appointment_date": TARGET_DAY, "time_slot": "09:00-10:00",
          "contact_name": "", "contact_phone": "13800138000"}, "请填写联系人姓名"),
        ({"appointment_date": TARGET_DAY, "time_slot": "09:00-10:00",
          "contact_name": "张三", "contact_phone": "138"}, "联系电话需为 11 位"),
    ],
)
def test_alt_a2_incomplete_form(client, normal_user, service, payload, expect_tip):
    _login(client)
    resp = client.post(f"/appointments/create/{service.id}", data=payload)
    assert resp.status_code == 200
    assert expect_tip.encode() in resp.data
    assert Appointment.query.count() == 0


def test_alt_a2_past_date_rejected(client, normal_user, service):
    _login(client)
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": yesterday, "time_slot": "09:00-10:00",
              "contact_name": "张三", "contact_phone": "13800138000"},
        follow_redirects=True,
    )
    assert "不能预约过去的日期".encode() in resp.data
    assert Appointment.query.count() == 0


def test_alt_a3_slot_full_rejected(client, normal_user, service):
    """备选流 A3：把容量为 2 的时段占满后，第三人提交被拒。"""
    _login(client)
    client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": TARGET_DAY, "time_slot": "09:00-10:00",
              "contact_name": "张三", "contact_phone": "13800138000"},
        follow_redirects=True,
    )
    # 第二个用户占掉最后一个名额
    u2 = User(username="lisi", email="lisi@example.com")
    u2.set_password("User@123")
    db.session.add(u2)
    db.session.commit()
    client.get("/auth/logout")
    client.post("/auth/login", data={"login": "lisi", "password": "User@123"})
    client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": TARGET_DAY, "time_slot": "09:00-10:00",
              "contact_name": "李四", "contact_phone": "13900139000"},
        follow_redirects=True,
    )
    assert service.daily_capacity == 2
    assert Appointment.query.count() == 2

    # 第三个用户：名额已满
    u3 = User(username="wangwu", email="wangwu@example.com")
    u3.set_password("User@123")
    db.session.add(u3)
    db.session.commit()
    client.get("/auth/logout")
    client.post("/auth/login", data={"login": "wangwu", "password": "User@123"})
    resp = client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": TARGET_DAY, "time_slot": "09:00-10:00",
              "contact_name": "王五", "contact_phone": "13700137000"},
        follow_redirects=True,
    )
    assert "名额已满".encode() in resp.data
    assert Appointment.query.count() == 2


def test_alt_a4_missing_csrf_token_rejected():
    """备选流 A4：开启 CSRF 防护后，缺少令牌的提交被拒绝（模拟异常/跨站提交）。"""
    from app import create_app
    from app.extensions import db as _db

    app = create_app("development")  # 开发配置：CSRF 防护开启
    assert app.config["WTF_CSRF_ENABLED"] is True
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        user = User(username="csrfuser", email="csrf@example.com")
        user.set_password("User@123")
        service_item = ServiceItem(
            name="CSRF 测试服务", category="life", description="用于 CSRF 场景测试",
            address="测试地址", price=10, duration_minutes=30,
            daily_capacity=2, status="online",
        )
        _db.session.add_all([user, service_item])
        _db.session.commit()

        c = app.test_client()
        c.post("/auth/login", data={"login": "csrfuser", "password": "User@123"})
        resp = c.post(
            f"/appointments/create/{service_item.id}",
            data={"appointment_date": TARGET_DAY, "time_slot": "09:00-10:00",
                  "contact_name": "张三", "contact_phone": "13800138000"},
        )
        assert resp.status_code == 400  # CSRF 校验失败，请求被拒绝
        assert _db.session.query(Appointment).count() == 0  # 未写入数据库
        _db.drop_all()
