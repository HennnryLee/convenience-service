"""实体辅助属性与 __repr__ 测试（可读日志/调试输出的基础）。"""
from datetime import date, timedelta

from app.models import Announcement, Feedback, ServiceItem, User


def test_user_repr_role_text_and_password_guard(app):
    user = User(username="repruser", email="repr@example.com", role="admin")
    user.set_password("User@123")
    assert "repruser" in repr(user)
    assert user.role_text == "管理员"
    assert user.is_admin is True
    assert User(username="nohash", email="nohash@example.com").check_password("x") is False


def test_announcement_summary_and_repr(app, admin_user):
    long_text = "公告正文" * 30
    ann = Announcement(title="摘要测试", content=long_text, author_id=admin_user.id)
    assert len(ann.summary) <= 61
    assert ann.summary.endswith("…")
    assert "摘要测试" in repr(ann)

    short = Announcement(title="短公告", content="很短", author_id=admin_user.id)
    assert short.summary == "很短"


def test_appointment_status_helpers_and_repr(app, user_factory, service_factory, appointment_factory):
    user = user_factory()
    service = service_factory(name="状态辅助服务")
    appt = appointment_factory(user, service, status="cancelled")
    assert appt.is_cancelled is True
    assert appt.status_text == "已取消"
    assert "cancelled" in repr(appt)

    appt.change_status("pending")
    assert appt.status == "pending"
    assert appt.updated_at is not None


def test_feedback_rating_text_and_repr(app, user_factory, service_factory, appointment_factory):
    user = user_factory()
    service = service_factory(name="评价文案服务")
    appt = appointment_factory(
        user, service, appointment_date=date.today() - timedelta(days=1), status="completed"
    )
    feedback = Feedback(
        user_id=user.id, service_id=service.id, appointment_id=appt.id, rating=5
    )
    assert feedback.rating_text == "非常满意"
    assert "rating=5" in repr(feedback)


def test_service_repr_and_flags(service_factory):
    service = service_factory(name="展示服务", status="offline")
    assert service.is_online is False
    assert "展示服务" in repr(service)
    assert isinstance(service, ServiceItem)


def test_service_name_validator_handles_non_string():
    """防御性：名称不是字符串时不应崩溃，拼音键回退为空串。"""
    service = ServiceItem()
    assert service._sync_name_pinyin("name", None) is None
    assert service.name_pinyin == ""
