"""预约服务（业务编排层）单元测试：验证数据持久化流程与业务规则协同。"""
from datetime import date, timedelta

from app.repositories import AppointmentRepository
from app.services.appointment_service import (
    cancel_appointment,
    change_status,
    create_appointment,
    get_slot_availability,
)
from app.utils.constants import TIME_SLOTS


def _create(user, service, day_offset=1, slot="09:00-10:00", phone="13800138000"):
    return create_appointment(
        user=user,
        service_id=service.id,
        appointment_date=date.today() + timedelta(days=day_offset),
        time_slot=slot,
        contact_name="张三",
        contact_phone=phone,
        remark="希望上午办理",
    )


def test_create_appointment_success(app, normal_user, service, tomorrow):
    appt, errors = create_appointment(
        user=normal_user, service_id=service.id, appointment_date=tomorrow,
        time_slot="09:00-10:00", contact_name="张三", contact_phone="13800138000")
    assert errors == [] and appt is not None
    assert appt.status == "pending"
    assert AppointmentRepository.get(appt.id).service.name == service.name


def test_create_appointment_rejects_bad_phone(app, normal_user, service, tomorrow):
    appt, errors = create_appointment(
        user=normal_user, service_id=service.id, appointment_date=tomorrow,
        time_slot="09:00-10:00", contact_name="张三", contact_phone="123")
    assert appt is None and any("手机号" in e for e in errors)


def _new_user(username, email):
    """测试辅助：直接落库创建一个用户。"""
    from app.extensions import db
    from app.models import User as UserModel

    user = UserModel(username=username, email=email)
    user.set_password("User@123")
    db.session.add(user)
    db.session.commit()
    return user


def test_capacity_is_enforced_end_to_end(app, normal_user, service, tomorrow):
    """同一时段容量为 2：前两人成功，第三人因满员被拒。"""
    u1, _ = _create(normal_user, service, slot="09:00-10:00")
    u2 = _new_user("lisi", "lisi@example.com")
    u2_appt, e2 = _create(u2, service, slot="09:00-10:00")
    assert u1 is not None and e2 == []

    u3 = _new_user("wangwu", "wangwu@example.com")
    u3_appt, e3 = _create(u3, service, slot="09:00-10:00")
    assert u3_appt is None and any("已满" in e for e in e3)

    # 换个时段仍可预约（容量按时段独立计算）
    u3_appt2, e4 = _create(u3, service, slot="10:00-11:00")
    assert u3_appt2 is not None and e4 == []


def test_duplicate_booking_is_rejected(app, normal_user, service, tomorrow):
    first, e1 = _create(normal_user, service, slot="09:00-10:00")
    second, e2 = _create(normal_user, service, slot="09:00-10:00")
    assert first is not None and e1 == []
    assert second is None and any("重复" in e for e in e2)

    # 取消后可以重新预约（已取消的记录不占用名额）
    ok, _ = cancel_appointment(first, normal_user)
    assert ok is True
    again, e3 = _create(normal_user, service, slot="09:00-10:00")
    assert again is not None and e3 == []


def test_cancel_by_owner_and_permission(app, normal_user, admin_user, service, appointment):
    ok, msg = cancel_appointment(appointment, normal_user)
    assert ok is True and appointment.status == "cancelled"

    appt2, _ = _create(normal_user, service, slot="10:00-11:00")
    ok2, msg2 = cancel_appointment(appt2, admin_user, is_admin=True)
    assert ok2 is True

    appt3, _ = _create(normal_user, service, slot="11:00-12:00")
    ok3, msg3 = cancel_appointment(appt3, admin_user, is_admin=False)
    assert ok3 is False and "本人" in msg3

    ok4, msg4 = cancel_appointment(appt3, normal_user)
    ok5, msg5 = cancel_appointment(appt3, normal_user)  # 已取消，重复取消
    assert ok4 is True and ok5 is False


def test_status_transition_service(app, normal_user, service, appointment):
    ok, msg = change_status(appointment, "completed")   # pending -> completed 非法
    assert ok is False and "不允许" in msg
    ok, _ = change_status(appointment, "confirmed")     # pending -> confirmed 合法
    assert ok is True and appointment.status == "confirmed"
    ok, _ = change_status(appointment, "completed")     # confirmed -> completed 合法
    assert ok is True and appointment.status == "completed"
    ok, _ = change_status(appointment, "confirmed")     # 终态回退，非法
    assert ok is False


def test_slot_availability(app, service, tomorrow):
    availability = get_slot_availability(service, tomorrow)
    assert len(availability) == len(TIME_SLOTS)
    assert availability[0]["slot"] == TIME_SLOTS[0]
    assert availability[0]["capacity"] == service.daily_capacity
    assert availability[0]["remaining"] == service.daily_capacity


def test_slot_availability_after_booking(app, normal_user, service, tomorrow):
    _create(normal_user, service, slot="09:00-10:00")
    availability = get_slot_availability(service, tomorrow)
    first = availability[0]
    assert first["remaining"] == service.daily_capacity - 1
    assert first["full"] is False
