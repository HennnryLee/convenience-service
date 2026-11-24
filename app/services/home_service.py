"""首页门户的应用服务：一次取齐热门服务与最新公告。"""
from __future__ import annotations

from app.repositories.announcement_repository import AnnouncementRepository
from app.repositories.service_repository import ServiceRepository


def get_home_data(hot_limit=3, announcement_limit=5):
    """首页数据；limits 可注入，便于测试边界。"""
    return {
        "hot_services": ServiceRepository.list_online(limit=hot_limit),
        "announcements": AnnouncementRepository.latest(limit=announcement_limit),
    }
