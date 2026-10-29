"""服务查询服务：关键词搜索、分类浏览、排序、详情与可用时段。"""
from app.config import Config
from app.repositories.service_repository import ServiceRepository
from app.services.appointment_service import get_slot_availability
from app.utils.constants import SERVICE_CATEGORIES, SORT_OPTIONS
from app.utils.validators import validate_keyword


def search_services(keyword=None, category=None, sort="default", page=1, per_page=None):
    """服务检索。

    前置条件：sort 必须是 SORT_OPTIONS 中的键（否则按 default 处理）。
    后置条件：返回 Flask-SQLAlchemy 的 Pagination 对象。
    """
    per_page = per_page or Config.ITEMS_PER_PAGE
    keyword = validate_keyword(keyword, max_length=Config.MAX_SEARCH_KEYWORD)
    if keyword is None:  # 超长关键词：返回空结果，由表现层给出提示
        keyword = " " * (Config.MAX_SEARCH_KEYWORD + 1)
    if sort not in SORT_OPTIONS:
        sort = "default"
    if category and category not in SERVICE_CATEGORIES:
        category = None
    return ServiceRepository.search(
        keyword=keyword or None,
        category=category,
        sort=sort,
        only_online=True,
        page=page,
        per_page=per_page,
    )


def get_service_detail(service_id):
    """服务详情：基本信息 + 今日各时段剩余名额 + 近期评价。"""
    from app.repositories.feedback_repository import FeedbackRepository

    service = ServiceRepository.get(service_id)
    if service is None:
        return None
    availability = get_slot_availability(service)
    feedbacks = FeedbackRepository.list_by_service(service_id, limit=5)
    return {"service": service, "availability": availability, "feedbacks": feedbacks}


def get_categories_with_count():
    """首页/列表页的分类导航（含每个分类的在线服务数量）。"""
    items = []
    for code, text in SERVICE_CATEGORIES.items():
        stmt_count = ServiceRepository.search(category=code, per_page=1).total
        items.append({"code": code, "text": text, "count": stmt_count})
    return items
