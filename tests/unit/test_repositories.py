"""数据访问层单元测试：验证增删改查（CRUD）操作的正确性。

被测：UserRepository / ServiceRepository / AppointmentRepository /
      AnnouncementRepository / FeedbackRepository
"""
from datetime import date, timedelta

from app.extensions import db
from app.models import Appointment, ServiceItem, User
from app.repositories import (
    AnnouncementRepository,
    AppointmentRepository,
    FeedbackRepository,
    ServiceRepository,
    UserRepository,
)


# ------------------------------------------------------------------ 用户 CRUD
def test_user_create_and_read(app):
    user = UserRepository.create("lisi", "lisi@example.com", "User@123", phone="13900139000")
    assert user.id is not None
    assert user.check_password("User@123") is True
    assert user.check_password("wrong") is False
    assert UserRepository.get(user.id).username == "lisi"
    assert UserRepository.get_by_username("lisi") is not None
    assert UserRepository.get_by_email("lisi@example.com") is not None
    assert UserRepository.get_by_login("lisi") is not None          # 用户名登录
    assert UserRepository.get_by_login("lisi@example.com") is not None  # 邮箱登录


def test_password_is_hashed_not_plaintext(app):
    user = UserRepository.create("wangwu", "ww@example.com", "User@123")
    assert user.password_hash != "User@123"
    assert "User@123" not in user.password_hash


def test_user_update_and_soft_disable(app, normal_user):
    UserRepository.update(normal_user, phone="13711112222", real_name="张三")
    assert normal_user.phone == "13711112222"
    assert normal_user.real_name == "张三"
    UserRepository.set_active(normal_user, False)
    assert normal_user.is_active is False


def test_user_delete(app, normal_user):
    uid = normal_user.id
    db.session.delete(normal_user)
    db.session.commit()
    assert UserRepository.get(uid) is None


def test_user_search_and_count(app, normal_user, admin_user):
    result = UserRepository.search(keyword="zhang", page=1, per_page=10)
    assert result.total == 1
    assert result.items[0].username == "zhangsan"
    assert UserRepository.count() == 2
    assert UserRepository.count(role="admin") == 1


# ------------------------------------------------------------------ 服务 CRUD
def test_service_create_read_update(app):
    svc = ServiceRepository.create(
        name="家庭水电维修", category="repair", price=50, daily_capacity=3
    )
    assert svc.id is not None and svc.is_online is True
    ServiceRepository.update(svc, price=80)
    assert float(ServiceRepository.get(svc.id).price) == 80.0
    ServiceRepository.set_status(svc, "offline")
    assert ServiceRepository.get(svc.id).is_online is False
    # 下架后不应出现在前台查询结果中
    assert ServiceRepository.search(only_online=True).total == 0
    assert ServiceRepository.search(only_online=False).total == 1


def test_service_search_by_keyword_and_category(app):
    ServiceRepository.create(name="身份证办理", category="government", description="政务")
    ServiceRepository.create(name="下水道疏通", category="life", description="生活")
    assert ServiceRepository.search(keyword="身份证").total == 1
    assert ServiceRepository.search(keyword="不存在的关键字").total == 0
    assert ServiceRepository.search(category="government").total == 1


def test_service_sort_and_pagination(app):
    ServiceRepository.create(name="便宜服务", category="life", price=10)
    ServiceRepository.create(name="贵价服务", category="life", price=999)
    asc = ServiceRepository.search(sort="price_asc", per_page=10).items
    assert float(asc[0].price) <= float(asc[1].price)
    desc = ServiceRepository.search(sort="price_desc", per_page=10).items
    assert float(desc[0].price) >= float(desc[1].price)
    page1 = ServiceRepository.search(per_page=1, page=1)
    assert page1.total == 2 and len(page1.items) == 1 and page1.pages == 2


# ------------------------------------------------------------------ 预约 CRUD
def test_appointment_create_and_query(app, normal_user, service, tomorrow):
    appt = AppointmentRepository.create(
        user_id=normal_user.id,
        service_id=service.id,
        appointment_date=tomorrow,
        time_slot="09:00-10:00",
        contact_name="张三",
        contact_phone="13800138000",
    )
    assert appt.status == "pending"
    assert AppointmentRepository.get(appt.id).user.username == "zhangsan"
    assert AppointmentRepository.list_by_user(normal_user.id).total == 1


def test_count_active_ignores_cancelled(app, normal_user, service, tomorrow):
    a1 = AppointmentRepository.create(
        user_id=normal_user.id, service_id=service.id, appointment_date=tomorrow,
        time_slot="09:00-10:00", contact_name="张三", contact_phone="13800138000")
    a2 = AppointmentRepository.create(
        user_id=normal_user.id, service_id=service.id, appointment_date=tomorrow,
        time_slot="09:00-10:00", contact_name="张三", contact_phone="13800138000", status="cancelled")
    assert AppointmentRepository.count_active(service.id, tomorrow, "09:00-10:00") == 1
    a1.change_status("cancelled")
    AppointmentRepository.save(a1)
    assert AppointmentRepository.count_active(service.id, tomorrow, "09:00-10:00") == 0
    assert AppointmentRepository.has_active_duplicate(
        normal_user.id, service.id, tomorrow, "09:00-10:00") is False


def test_appointment_filters_for_admin(app, normal_user, service, appointment, tomorrow):
    assert AppointmentRepository.list_all(status="pending").total == 1
    assert AppointmentRepository.list_all(status="completed").total == 0
    assert AppointmentRepository.list_all(service_id=service.id).total == 1
    assert AppointmentRepository.list_all(target_date=tomorrow).total == 1
    assert AppointmentRepository.count_by_status("pending") == 1


def test_appointment_delete(app, appointment):
    aid = appointment.id
    db.session.delete(appointment)
    db.session.commit()
    assert AppointmentRepository.get(aid) is None


# ------------------------------------------------------------------ 公告 / 评价
def test_announcement_crud(app, admin_user):
    ann = AnnouncementRepository.create("停水通知", "本周六 9:00-15:00 停水", author_id=admin_user.id)
    assert AnnouncementRepository.get(ann.id).title == "停水通知"
    assert AnnouncementRepository.search(keyword="停水").total == 1
    AnnouncementRepository.update(ann, is_published=False)
    assert AnnouncementRepository.search(only_published=True).total == 0
    AnnouncementRepository.delete(ann)
    assert AnnouncementRepository.get(ann.id) is None


def test_feedback_crud_and_average(app, normal_user, service, appointment):
    fb = FeedbackRepository.create(
        user_id=normal_user.id, service_id=service.id, appointment_id=appointment.id,
        rating=4, content="还不错")
    assert FeedbackRepository.get_by_appointment(appointment.id) is not None
    assert FeedbackRepository.list_by_user(normal_user.id).total == 1
    assert round(float(FeedbackRepository.average_rating(service.id)), 1) == 4.0
    assert FeedbackRepository.count_all() == 1
    db.session.delete(fb)
    db.session.commit()
    assert FeedbackRepository.count_all() == 0
