"""后台概览、首页门户与公告服务的应用服务测试。"""
from datetime import date

from app.extensions import db
from app.models import Announcement
from app.services.announcement_service import (
    get_published_announcement,
    latest_announcements,
    search_announcements_page,
)
from app.services.dashboard_service import get_dashboard_stats
from app.services.home_service import get_home_data


def test_dashboard_stats_aggregates_all_counts(
    app, user_factory, service_factory, appointment_factory
):
    admin = user_factory(role="admin")
    user = user_factory()
    online = service_factory(name="在线服务")
    service_factory(name="下架服务", status="offline")
    appointment_factory(user, online, status="pending")
    appointment_factory(user, online, status="confirmed")

    stats = get_dashboard_stats(today=date(2026, 1, 1))
    assert stats["users"] == 2
    assert stats["services"] == 1
    assert stats["appointments"] == 2
    assert stats["pending"] == 1
    assert stats["today"] == 0
    assert stats["feedbacks"] == 0
    assert admin.id is not None


def test_home_data_respects_limits(app, service_factory, admin_user):
    for index in range(5):
        service_factory(name=f"首页服务{index}")
    for index in range(6):
        db.session.add(Announcement(
            title=f"公告{index}", content="内容", author_id=admin_user.id, is_published=True
        ))
    db.session.commit()

    data = get_home_data(hot_limit=3, announcement_limit=2)
    assert len(data["hot_services"]) == 3
    assert len(data["announcements"]) == 2


def test_announcement_search_only_published(app, admin_user):
    db.session.add_all([
        Announcement(title="已发布公告", content="正文", author_id=admin_user.id, is_published=True),
        Announcement(title="草稿公告", content="正文", author_id=admin_user.id, is_published=False),
    ])
    db.session.commit()

    outcome = search_announcements_page()
    assert outcome.pagination.total == 1
    assert outcome.pagination.items[0].title == "已发布公告"


def test_announcement_search_keyword_and_no_match(app, announcement):
    matched = search_announcements_page(keyword="延时")
    assert matched.pagination.total == 1

    missing = search_announcements_page(keyword="不存在")
    assert missing.pagination.total == 0
    assert "没有找到相关公告" in missing.message


def test_announcement_search_escapes_like_wildcards(app, admin_user):
    db.session.add_all([
        Announcement(title="普通公告", content="正文", author_id=admin_user.id, is_published=True),
        Announcement(title="折扣100%公告", content="正文", author_id=admin_user.id, is_published=True),
        Announcement(title="下划线_公告", content="正文", author_id=admin_user.id, is_published=True),
    ])
    db.session.commit()

    percent = search_announcements_page(keyword="%")
    underscore = search_announcements_page(keyword="_")
    assert percent.pagination.total == 1
    assert percent.pagination.items[0].title == "折扣100%公告"
    assert underscore.pagination.total == 1
    assert underscore.pagination.items[0].title == "下划线_公告"


def test_announcement_keyword_over_limit(app):
    outcome = search_announcements_page(keyword="a" * 51)
    assert outcome.pagination is None
    assert "不能超过 50" in outcome.message


def test_get_published_announcement_hides_draft(app, admin_user):
    draft = Announcement(title="草稿", content="正文", author_id=admin_user.id, is_published=False)
    db.session.add(draft)
    db.session.commit()

    assert get_published_announcement(draft.id) is None
    assert get_published_announcement(99999) is None


def test_latest_announcements_limit_and_order(app, admin_user):
    for index in range(4):
        db.session.add(Announcement(
            title=f"公告{index}", content="正文", author_id=admin_user.id, is_published=True
        ))
    db.session.commit()

    latest = latest_announcements(limit=2)
    assert len(latest) == 2
    assert latest[0].id > latest[1].id
