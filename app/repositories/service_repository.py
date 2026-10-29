"""服务项目数据访问层。"""
from sqlalchemy import func, select

from app.extensions import db
from app.models.appointment import Appointment
from app.models.service import ServiceItem
from app.repositories.base import BaseRepository

# 排序方式 -> 排序表达式工厂（表驱动：新增排序只改这张表）
SORT_EXPRESSIONS = {
    "name": lambda: ServiceItem.name.asc(),
    "price_asc": lambda: ServiceItem.price.asc(),
    "price_desc": lambda: ServiceItem.price.desc(),
    "popular": lambda: func.count(Appointment.id).desc(),
    "default": lambda: ServiceItem.created_at.desc(),
}


class ServiceRepository(BaseRepository):
    model = ServiceItem

    @staticmethod
    def get_by_name(name):
        return db.session.scalar(select(ServiceItem).where(ServiceItem.name == name))

    @classmethod
    def create(cls, **fields):
        return cls.add(ServiceItem(**fields))

    @classmethod
    def set_status(cls, service, status):
        """上架 / 下架（软删除：保留历史预约的外键完整性）。"""
        service.status = status
        return cls.save(service)

    @staticmethod
    def search(keyword=None, category=None, sort="default", only_online=True, page=1, per_page=9):
        """服务查询：关键词（名称或简介）+ 分类 + 排序 + 分页。"""
        stmt = select(ServiceItem)
        if only_online:
            stmt = stmt.where(ServiceItem.status == "online")
        if category:
            stmt = stmt.where(ServiceItem.category == category)
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                ServiceItem.name.like(pattern) | ServiceItem.description.like(pattern)
            )
        if sort == "popular":
            stmt = stmt.outerjoin(Appointment).group_by(ServiceItem.id)
        stmt = stmt.order_by(SORT_EXPRESSIONS.get(sort, SORT_EXPRESSIONS["default"])(),
                             ServiceItem.id.asc())
        return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def list_online(limit=None):
        stmt = select(ServiceItem).where(ServiceItem.status == "online").order_by(ServiceItem.id)
        if limit:
            stmt = stmt.limit(limit)
        return list(db.session.scalars(stmt))

    @staticmethod
    def count_by_status(status):
        return db.session.scalar(
            select(func.count()).select_from(ServiceItem).where(ServiceItem.status == status)
        )
