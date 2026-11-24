"""服务查询的应用服务：参数校验 → 查询 → 给表现层一个可直接渲染的结果。

视图层不再关心"关键词超长该不该查库""分类码非法怎么办"，
只负责把 ``outcome.message`` 转成 flash、把 ``outcome.pagination`` 交给模板。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import Config
from app.repositories.service_repository import ServiceRepository
from app.utils.constants import SERVICE_CATEGORIES, SORT_OPTIONS
from app.utils.validators import validate_keyword


@dataclass(frozen=True)
class ServiceSearchOutcome:
    """服务查询结果（pagination 为 None 表示参数非法、未执行查询）。"""

    pagination: object | None
    keyword: str
    message: str | None = None


def search_service_page(
    keyword=None,
    category=None,
    sort="default",
    page=1,
    per_page=None,
    max_keyword_length=None,
):
    """服务列表页查询。

    前置条件：page 为整数（视图层已用 parse_page 规整）。
    后置条件：返回 ServiceSearchOutcome；pagination 为 Flask-SQLAlchemy Pagination。
    """
    per_page = per_page or Config.ITEMS_PER_PAGE
    max_keyword_length = max_keyword_length or Config.MAX_SEARCH_KEYWORD
    keyword = (keyword or "").strip()

    validated = validate_keyword(keyword, max_length=max_keyword_length)
    if validated is None:
        return ServiceSearchOutcome(
            pagination=None,
            keyword=keyword,
            message=f"搜索关键词不能超过 {max_keyword_length} 个字符。",
        )

    if sort not in SORT_OPTIONS:
        sort = "default"
    if category and category not in SERVICE_CATEGORIES:
        category = None

    pagination = ServiceRepository.search(
        keyword=validated or None,
        category=category,
        sort=sort,
        only_online=True,
        page=page,
        per_page=per_page,
    )
    message = None
    if pagination.total == 0:
        message = "没有找到匹配的服务，请尝试其它关键词或分类。"
    return ServiceSearchOutcome(pagination=pagination, keyword=validated, message=message)
