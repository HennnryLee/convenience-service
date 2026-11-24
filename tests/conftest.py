"""pytest 公共夹具：为每个用例创建独立的应用与内存数据库，保证测试可重复。

2026-11-24 工程化改进：
  - 按目录自动打 marker（unit/functional/integration/system），新增用例无需手工标注；
  - 提供 user_factory / service_factory / appointment_factory，减少重复造数；
  - 所有夹具仍使用 testing 配置的内存库，绝不触碰 instance/app.db。
"""
from datetime import date, timedelta
from itertools import count

import pytest
from app import create_app
from app.extensions import db
from app.models import Announcement, Appointment, Feedback, ServiceItem, User

_MARKER_BY_DIR = {"unit", "functional", "integration", "system"}


def pytest_collection_modifyitems(config, items):
    """按测试所在目录自动追加 marker，pytest -m unit 等命令无需逐文件声明。"""
    for item in items:
        for part in item.path.parts:
            if part in _MARKER_BY_DIR:
                item.add_marker(getattr(pytest.mark, part))
                break


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def normal_user(app):
    user = User(username="zhangsan", email="zhangsan@example.com", role="user")
    user.set_password("User@123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def admin_user(app):
    user = User(username="admin", email="admin@example.com", role="admin")
    user.set_password("Admin@123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def service(app):
    item = ServiceItem(
        name="身份证换领办理",
        category="government",
        description="居民身份证到期换领、遗失补办等政务服务。",
        address="市民之家 A 区 3 号窗口",
        price=20.00,
        duration_minutes=30,
        daily_capacity=2,
        status="online",
    )
    db.session.add(item)
    db.session.commit()
    return item


@pytest.fixture()
def tomorrow():
    return date.today() + timedelta(days=1)


@pytest.fixture()
def appointment(app, normal_user, service, tomorrow):
    appt = Appointment(
        user_id=normal_user.id,
        service_id=service.id,
        appointment_date=tomorrow,
        time_slot="09:00-10:00",
        contact_name="张三",
        contact_phone="13800138000",
        status="pending",
    )
    db.session.add(appt)
    db.session.commit()
    return appt


@pytest.fixture()
def announcement(app, admin_user):
    ann = Announcement(
        title="市民之家周末延时服务通知",
        content="自本月起，市民之家周六上午 9:00-12:00 提供延时服务。",
        author_id=admin_user.id,
        is_published=True,
    )
    db.session.add(ann)
    db.session.commit()
    return ann


@pytest.fixture()
def feedback(app, normal_user, service, appointment):
    appointment.status = "completed"
    fb = Feedback(
        user_id=normal_user.id,
        service_id=service.id,
        appointment_id=appointment.id,
        rating=5,
        content="办理速度快，服务态度好。",
    )
    db.session.add(fb)
    db.session.commit()
    return fb


# ------------------------------------------------------------------ 工厂夹具
@pytest.fixture()
def user_factory(app):
    """按需创建用户；默认唯一用户名/邮箱，避免唯一约束互相干扰。"""
    seq = count(1)

    def _make(username=None, email=None, role="user", password="User@123", active=True, **fields):
        index = next(seq)
        username = username or f"user{index}"
        user = User(
            username=username,
            email=email or f"{username}@example.com",
            role=role,
            is_active=active,
            **fields,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make


@pytest.fixture()
def service_factory(app):
    """按需创建服务项目；默认保证名称唯一。"""
    seq = count(1)

    def _make(name=None, category="life", price=10, capacity=3, status="online", **fields):
        item = ServiceItem(
            name=name or f"测试服务{next(seq)}",
            category=category,
            description=fields.pop("description", "用于测试的服务项目。"),
            address=fields.pop("address", "测试地址"),
            price=price,
            duration_minutes=fields.pop("duration_minutes", 30),
            daily_capacity=capacity,
            status=status,
            **fields,
        )
        db.session.add(item)
        db.session.commit()
        return item

    return _make


@pytest.fixture()
def appointment_factory(app):
    """按需创建预约；日期默认明天，状态默认为待确认。"""
    seq = count(1)

    def _make(user, service, appointment_date=None, slot="09:00-10:00", status="pending", **fields):
        appt = Appointment(
            user_id=user.id,
            service_id=service.id,
            appointment_date=appointment_date or (date.today() + timedelta(days=1)),
            time_slot=slot,
            contact_name=fields.pop("contact_name", "张三"),
            contact_phone=fields.pop("contact_phone", "13800138000"),
            remark=fields.pop("remark", f"测试预约{next(seq)}"),
            status=status,
            **fields,
        )
        db.session.add(appt)
        db.session.commit()
        return appt

    return _make

