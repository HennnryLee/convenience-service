"""课程级可用性优化回归：500 修复、表单预填、默认日期、时段提示、确认与可访问性。"""
from datetime import date, datetime, time, timedelta

from app.extensions import db
from app.models import ServiceItem
from app.services.appointment_service import default_booking_date
from app.services.service_catalog import get_service_detail


def test_service_without_description_renders_list(client, app, service_factory):
    """后台允许简介为空；列表页不能再因 None[:50] 崩溃。"""
    service_factory(name="无简介服务", description=None)
    response = client.get("/services/")
    assert response.status_code == 200
    assert "暂无简介" in response.get_data(as_text=True)


def test_service_summary_property_truncates_and_falls_back(app):
    long_service = ServiceItem(
        name="长简介服务", category="life", description="x" * 60, price=1, daily_capacity=1
    )
    assert long_service.summary.endswith("…")
    assert len(long_service.summary) == 51

    empty_service = ServiceItem(name="空简介服务", category="life", description="", price=1, daily_capacity=1)
    assert empty_service.summary == "暂无简介"


def test_booking_form_prefills_profile_and_limits_date(client, normal_user, service):
    normal_user.real_name = "张三"
    normal_user.phone = "13800138000"
    db.session.commit()
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})

    response = client.get(f"/appointments/create/{service.id}")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'value="张三"' in body
    assert 'value="13800138000"' in body
    today = date.today()
    assert f'min="{today.isoformat()}"' in body
    assert f'max="{(today + timedelta(days=30)).isoformat()}"' in body


def test_default_booking_date_skips_fully_past_today(service, monkeypatch):
    fixed_now = datetime.combine(date.today(), time(20, 0))
    monkeypatch.setattr(
        "app.services.appointment_service.get_slot_availability",
        lambda *args, **kwargs: [
            {"remaining": 1, "past": True, "full": False},
            {"remaining": 0, "past": False, "full": True},
        ],
    )
    assert default_booking_date(service, now=fixed_now) == date.today() + timedelta(days=1)


def test_default_booking_date_keeps_today_when_slot_available(service, monkeypatch):
    fixed_now = datetime.combine(date.today(), time(8, 0))
    monkeypatch.setattr(
        "app.services.appointment_service.get_slot_availability",
        lambda *args, **kwargs: [{"remaining": 1, "past": False, "full": False}],
    )
    assert default_booking_date(service, now=fixed_now) == date.today()


def test_booking_form_survives_when_all_slots_are_full(client, normal_user, service, monkeypatch):
    """所有时段都满时，表单仍应正常渲染（不能因为找不到默认时段而崩）。"""
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    monkeypatch.setattr(
        "app.modules.appointments.default_booking_date",
        lambda *args, **kwargs: date.today() + timedelta(days=1),
    )
    monkeypatch.setattr(
        "app.modules.appointments.get_slot_availability",
        lambda *args, **kwargs: [
            {"slot": "09:00-10:00", "remaining": 0, "past": False, "full": True}
        ],
    )
    response = client.get(f"/appointments/create/{service.id}")
    assert response.status_code == 200
    assert "09:00-10:00" in response.get_data(as_text=True)


def test_service_detail_flags_no_available_today(service):
    today = date.today()
    available = get_service_detail(service.id, now=datetime.combine(today, time(8, 0)))
    ended = get_service_detail(service.id, now=datetime.combine(today, time(20, 0)))

    assert available["has_available_today"] is True
    assert ended["has_available_today"] is False


def test_destructive_actions_are_marked_for_confirmation(client, normal_user, service, appointment):
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    body = client.get("/appointments/mine").get_data(as_text=True)
    assert 'data-confirm="确定取消这条预约吗' in body


def test_search_form_has_screen_reader_labels(client):
    body = client.get("/services/").get_data(as_text=True)
    assert 'class="sr-only" for="keyword"' in body
    assert 'class="sr-only" for="category"' in body
    assert 'class="sr-only" for="sort"' in body
