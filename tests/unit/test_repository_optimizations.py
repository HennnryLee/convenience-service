"""数据访问层优化后的查询行为测试（N+1 消除、聚合、可评价列表）。"""
from datetime import date, timedelta

from app.extensions import db
from app.models import Feedback
from app.repositories import AppointmentRepository, FeedbackRepository


def test_list_reviewable_returns_only_completed_without_feedback(
    app, user_factory, service_factory, appointment_factory
):
    user = user_factory()
    other = user_factory()
    service = service_factory(name="评价服务")

    completed = appointment_factory(user, service, status="completed")
    appointment_factory(user, service, status="pending", slot="10:00-11:00")
    appointment_factory(other, service, status="completed", slot="11:00-12:00")
    reviewed = appointment_factory(
        user, service, status="completed", slot="14:00-15:00"
    )
    db.session.add(Feedback(
        user_id=user.id, service_id=service.id, appointment_id=reviewed.id, rating=5
    ))
    db.session.commit()

    rows = AppointmentRepository.list_reviewable_by_user(user.id)
    assert [row.id for row in rows] == [completed.id]


def test_list_reviewable_orders_by_date_desc(
    app, user_factory, service_factory, appointment_factory
):
    user = user_factory()
    service = service_factory(name="排序服务")
    older = appointment_factory(
        user, service, appointment_date=date.today() - timedelta(days=2),
        status="completed", slot="09:00-10:00",
    )
    newer = appointment_factory(
        user, service, appointment_date=date.today() - timedelta(days=1),
        status="completed", slot="09:00-10:00",
    )

    rows = AppointmentRepository.list_reviewable_by_user(user.id)
    assert [row.id for row in rows] == [newer.id, older.id]


def test_average_rating_and_empty_service(
    app, user_factory, service_factory, appointment_factory
):
    user = user_factory()
    service = service_factory(name="评分服务")
    empty_service = service_factory(name="无评分服务")

    for index, rating in enumerate((3, 5), start=1):
        appt = appointment_factory(user, service, status="completed", slot=f"{8 + index}:00-{9 + index}:00")
        db.session.add(Feedback(
            user_id=user.id, service_id=service.id, appointment_id=appt.id, rating=rating
        ))
    db.session.commit()

    assert round(float(FeedbackRepository.average_rating(service.id)), 1) == 4.0
    assert FeedbackRepository.average_rating(empty_service.id) is None


def test_count_active_ignores_cancelled(app, user_factory, service_factory, appointment_factory):
    user = user_factory()
    service = service_factory(name="容量服务", capacity=2)
    day = date.today() + timedelta(days=1)

    appointment_factory(user, service, appointment_date=day, status="pending")
    appointment_factory(user, service, appointment_date=day, status="confirmed")
    appointment_factory(user, service, appointment_date=day, status="cancelled")

    assert AppointmentRepository.count_active(service.id, day, "09:00-10:00") == 2


def test_list_all_supports_combined_filters(app, user_factory, service_factory, appointment_factory):
    first = user_factory()
    second = user_factory()
    service = service_factory(name="筛选服务")
    day = date.today() + timedelta(days=3)

    appointment_factory(first, service, appointment_date=day, status="pending")
    appointment_factory(second, service, appointment_date=day, status="confirmed")

    by_user = AppointmentRepository.list_all(user_id=first.id)
    by_status = AppointmentRepository.list_all(status="confirmed")
    by_date = AppointmentRepository.list_all(target_date=day)
    combined = AppointmentRepository.list_all(user_id=second.id, status="confirmed", target_date=day)

    assert by_user.total == 1
    assert by_status.total == 1
    assert by_date.total == 2
    assert combined.total == 1


def test_base_repository_get_and_optional_commit(app, service_factory):
    from app.repositories import ServiceRepository

    assert ServiceRepository.get(99999) is None
    assert ServiceRepository.get(None) is None

    # commit=False：只加入会话，由上层统一提交（为多表事务预留）
    pending = ServiceRepository.add(
        ServiceRepository.model(name="延迟提交服务", category="life", price=1, daily_capacity=1),
        commit=False,
    )
    db.session.flush()
    assert db.session.get(ServiceRepository.model, pending.id) is pending
    db.session.rollback()
    assert ServiceRepository.get_by_name("延迟提交服务") is None

    # update(commit=False)：字段已修改但需显式保存
    service = service_factory(name="批量更新服务")
    ServiceRepository.update(service, commit=False, price=66)
    assert service.price == 66
    db.session.commit()


def test_repository_lookup_none_and_role_count(app, user_factory):
    from app.repositories import UserRepository

    assert UserRepository.get_by_email(None) is None
    assert UserRepository.get_by_email("") is None
    assert UserRepository.get_by_login(None) is None
    assert UserRepository.get_by_login("") is None

    user_factory(role="admin")
    user_factory(role="user")
    user_factory(role="user")
    assert UserRepository.count() == 3
    assert UserRepository.count(role="admin") == 1
    assert UserRepository.count(role="user") == 2


def test_feedback_lookup_by_appointment_and_missing(app, user_factory, service_factory, appointment_factory):
    from app.models import Feedback
    from app.repositories import FeedbackRepository

    user = user_factory()
    service = service_factory(name="评价查询服务")
    appt = appointment_factory(user, service, status="completed")
    assert FeedbackRepository.get_by_appointment(appt.id) is None

    feedback = Feedback(
        user_id=user.id, service_id=service.id, appointment_id=appt.id, rating=4
    )
    db.session.add(feedback)
    db.session.commit()
    assert FeedbackRepository.get_by_appointment(appt.id) is feedback


def test_service_search_popular_sort_and_online_listing(app, user_factory, service_factory, appointment_factory):
    from app.repositories import ServiceRepository

    user = user_factory()
    hot = service_factory(name="热门服务")
    cold = service_factory(name="冷门服务")
    appointment_factory(user, hot, status="pending")
    appointment_factory(user, cold, status="pending")
    appointment_factory(user, hot, status="pending", slot="10:00-11:00")

    popular = ServiceRepository.search(sort="popular")
    assert [item.id for item in popular.items][0] == hot.id

    assert len(ServiceRepository.list_online()) == 2
    assert len(ServiceRepository.list_online(limit=1)) == 1
    assert ServiceRepository.get_by_name("") is None
    assert ServiceRepository.count_by_status("online") == 2


def test_user_search_by_role_and_keyword(app, user_factory):
    from app.repositories import UserRepository

    alice = user_factory(username="alice", real_name="爱丽丝")
    user_factory(username="bob", real_name="鲍勃", role="admin")

    by_role = UserRepository.search(role="admin")
    by_keyword = UserRepository.search(keyword="爱丽")
    assert by_role.total == 1
    assert by_role.items[0].role == "admin"
    assert by_keyword.total == 1
    assert by_keyword.items[0].id == alice.id


def test_announcement_repository_can_include_unpublished(app, admin_user):
    from app.models import Announcement
    from app.repositories import AnnouncementRepository

    db.session.add_all([
        Announcement(title="已发布", content="正文", author_id=admin_user.id, is_published=True),
        Announcement(title="未发布", content="正文", author_id=admin_user.id, is_published=False),
    ])
    db.session.commit()

    assert AnnouncementRepository.search(only_published=True).total == 1
    assert AnnouncementRepository.search(only_published=False).total == 2
    assert AnnouncementRepository.search(keyword="未发布", only_published=False).total == 1


def test_list_by_service_date_only_active(app, user_factory, service_factory, appointment_factory):
    user = user_factory()
    service = service_factory(name="按日查询服务")
    target = date.today() + timedelta(days=2)
    active = appointment_factory(user, service, appointment_date=target, status="pending")
    appointment_factory(user, service, appointment_date=target, status="cancelled", slot="10:00-11:00")

    rows = AppointmentRepository.list_by_service_date(service.id, target)
    assert [row.id for row in rows] == [active.id]



