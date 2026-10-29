"""pytest 公共夹具：为每个用例创建独立的应用与内存数据库，保证测试可重复。"""
from datetime import date, timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models import Announcement, Appointment, Feedback, ServiceItem, User


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
