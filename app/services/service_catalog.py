"""服务查询服务：分类浏览、详情与可用时段。

列表检索已上移到 ``search_service``（参数校验 + 查询 + 提示语一次完成），
本模块保留详情页编排与分类导航统计。
"""
from __future__ import annotations

from datetime import datetime

from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.service_repository import ServiceRepository
from app.services.appointment_service import get_slot_availability
from app.services.search_service import search_service_page
from app.utils.constants import SERVICE_CATEGORIES
from app.utils.table_driven import category_badge, duration_level, price_level


def search_services(keyword=None, category=None, sort="default", page=1, per_page=None):
    """兼容旧调用：返回分页对象（参数非法时返回 None）。

    新代码请直接使用 ``app.services.search_service.search_service_page``，
    它能同时拿到提示语，避免视图层再判一次 total。
    """
    return search_service_page(
        keyword=keyword, category=category, sort=sort, page=page, per_page=per_page
    ).pagination


def get_service_detail(service_id, now=None):
    """服务详情：基本信息 + 今日各时段剩余名额 + 近期评价。

    now 可注入，便于测试"当天已过时段"的展示；默认取系统当前时刻。
    后置条件：服务存在时返回 dict，且含 price_level / duration_level 两个表驱动派生字段
    （阶梯访问与索引访问的结果，供页面直接展示，避免模板里写 if/elif）。
    """
    service = ServiceRepository.get(service_id)
    if service is None:
        return None
    availability = get_slot_availability(service, now=now or datetime.now())
    feedbacks = FeedbackRepository.list_by_service(service_id, limit=5)
    rating = FeedbackRepository.average_rating(service_id)
    has_available_today = any(
        item["remaining"] > 0 and not item["past"] for item in availability
    )
    return {
        "service": service,
        "availability": availability,
        "has_available_today": has_available_today,
        "feedbacks": feedbacks,
        "average_rating": round(float(rating), 1) if rating is not None else None,
        "price_level": price_level(service.price),
        "duration_level": duration_level(service.duration_minutes),
        "category_badge": category_badge(service.category),
    }


def get_categories_with_count():
    """首页/列表页的分类导航（含每个分类的在线服务数量）。

    使用一次 GROUP BY 聚合替代"每个分类一次分页查询"，分类越多收益越明显。
    """
    counts = ServiceRepository.counts_by_category(only_online=True)
    return [
        {"code": code, "text": text, "count": counts.get(code, 0)}
        for code, text in SERVICE_CATEGORIES.items()
    ]
