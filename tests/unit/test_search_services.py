"""服务查询应用服务测试（等价类 / 边界值 / 排序 / 分页）。

覆盖 `search_service_page` 的参数校验、白名单、空结果提示与分页行为，
以及 `service_catalog` 的分类计数与详情页聚合。
"""
from datetime import datetime

from app.repositories import ServiceRepository
from app.services.search_service import search_service_page
from app.services.service_catalog import get_categories_with_count, get_service_detail
from app.utils.constants import SERVICE_CATEGORIES


def test_keyword_empty_returns_all_online(service_factory):
    service_factory(name="在线服务A")
    service_factory(name="在线服务B")
    service_factory(name="下架服务", status="offline")

    outcome = search_service_page(keyword="")
    assert outcome.pagination is not None
    assert outcome.pagination.total == 2
    assert outcome.message is None


def test_keyword_matches_name_and_description(service_factory):
    service_factory(name="社保卡申领", description="社会保障卡首次申领")
    service_factory(name="身份证换领", description="居民身份证到期换领")

    by_name = search_service_page(keyword="社保")
    by_description = search_service_page(keyword="居民身份证")
    assert by_name.pagination.total == 1
    assert by_description.pagination.total == 1


def test_keyword_at_limit_is_accepted(service_factory):
    service_factory(name="a" * 50)
    outcome = search_service_page(keyword="a" * 50)
    assert outcome.pagination is not None
    assert outcome.pagination.total == 1
    assert outcome.message is None


def test_keyword_over_limit_returns_no_query(service_factory):
    service_factory(name="边界关键词服务")
    outcome = search_service_page(keyword="a" * 51)
    assert outcome.pagination is None
    assert "不能超过 50" in outcome.message


def test_invalid_category_and_sort_fall_back(service_factory):
    service_factory(name="分类回退服务", category="life")
    outcome = search_service_page(category="not-a-category", sort="not-a-sort")
    assert outcome.pagination.total == 1
    assert outcome.keyword == ""


def test_no_match_returns_info_message(service_factory):
    service_factory(name="唯一服务")
    outcome = search_service_page(keyword="不存在的关键词")
    assert outcome.pagination.total == 0
    assert "没有找到匹配的服务" in outcome.message


def test_sort_name_uses_pinyin(service_factory):
    service_factory(name="重庆小面")
    service_factory(name="北京烤鸭")
    outcome = search_service_page(sort="name")
    names = [item.name for item in outcome.pagination.items]
    assert names == ["北京烤鸭", "重庆小面"]


def test_pagination_respects_per_page(service_factory):
    for index in range(5):
        service_factory(name=f"分页服务{index}")
    outcome = search_service_page(page=2, per_page=2)
    assert outcome.pagination.page == 2
    assert len(outcome.pagination.items) == 2
    assert outcome.pagination.total == 5


def test_categories_with_count_uses_one_grouped_query(service_factory):
    service_factory(name="生活一", category="life")
    service_factory(name="生活二", category="life")
    service_factory(name="医疗一", category="medical")
    service_factory(name="已下架", category="medical", status="offline")

    rows = {item["code"]: item["count"] for item in get_categories_with_count()}
    assert rows["life"] == 2
    assert rows["medical"] == 1
    assert set(rows) == set(SERVICE_CATEGORIES)


def test_get_service_detail_returns_derived_fields_and_rating(
    service_factory, user_factory, appointment_factory
):
    service = service_factory(name="详情页服务", category="repair", price=88, duration_minutes=90)
    user = user_factory()
    appt = appointment_factory(user, service, status="completed")
    from app.extensions import db
    from app.models import Feedback

    db.session.add(Feedback(
        user_id=user.id, service_id=service.id, appointment_id=appt.id, rating=4
    ))
    db.session.commit()

    detail = get_service_detail(service.id, now=datetime(2026, 1, 1, 9, 30))
    assert detail["service"].id == service.id
    assert detail["average_rating"] == 4.0
    assert detail["price_level"] == "较高"
    assert detail["duration_level"] == "较慢"
    assert detail["category_badge"] == "维修"
    assert len(detail["availability"]) == 6


def test_get_service_detail_returns_none_for_missing(app):
    assert get_service_detail(99999) is None


def test_service_repository_counts_by_category(service_factory):
    service_factory(name="生活服务", category="life")
    service_factory(name="下线生活服务", category="life", status="offline")

    online = ServiceRepository.counts_by_category(only_online=True)
    all_rows = ServiceRepository.counts_by_category(only_online=False)
    assert online == {"life": 1}
    assert all_rows == {"life": 2}


def test_legacy_search_services_alias_returns_pagination(service_factory):
    from app.services.service_catalog import search_services

    service_factory(name="别名查询服务")
    pagination = search_services(keyword="别名")
    assert pagination is not None
    assert pagination.total == 1
