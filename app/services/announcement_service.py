"""公告资讯的应用服务：列表查询、详情可见性判断、首页最新公告。"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import Config
from app.repositories.announcement_repository import AnnouncementRepository
from app.utils.validators import validate_keyword


@dataclass(frozen=True)
class AnnouncementSearchOutcome:
    pagination: object | None
    keyword: str
    message: str | None = None


def search_announcements_page(keyword=None, page=1, per_page=None, max_keyword_length=None):
    """公告列表页查询（只返回已发布公告）。"""
    per_page = per_page or Config.ADMIN_ITEMS_PER_PAGE
    max_keyword_length = max_keyword_length or Config.MAX_SEARCH_KEYWORD
    keyword = (keyword or "").strip()

    validated = validate_keyword(keyword, max_length=max_keyword_length)
    if validated is None:
        return AnnouncementSearchOutcome(
            pagination=None,
            keyword=keyword,
            message=f"搜索关键词不能超过 {max_keyword_length} 个字符。",
        )

    pagination = AnnouncementRepository.search(
        keyword=validated or None, only_published=True, page=page, per_page=per_page
    )
    message = None
    if pagination.total == 0:
        message = "没有找到相关公告。"
    return AnnouncementSearchOutcome(pagination=pagination, keyword=validated, message=message)


def get_published_announcement(announcement_id):
    """取已发布公告；不存在或未发布都返回 None（对外不区分，避免泄露草稿）。"""
    announcement = AnnouncementRepository.get(announcement_id)
    if announcement is None or not announcement.is_published:
        return None
    return announcement


def latest_announcements(limit=5):
    return AnnouncementRepository.latest(limit=limit)
