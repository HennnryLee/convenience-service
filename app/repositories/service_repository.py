"""服务项目数据访问层。"""
from sqlalchemy import func, select

from app.extensions import db
from app.models.appointment import Appointment
from app.models.service import ServiceItem
from app.repositories.base import BaseRepository

# 排序方式 -> 排序表达式工厂（表驱动：新增排序只改这张表）
SORT_EXPRESSIONS = {
    # 不直接用 name.asc()：SQLite 的 BINARY 排序规则按 UTF-8 字节序比较，
    # 结果是 Unicode 码点序（住 → 儿 → 家 → 成 …），不是拼音也不是笔画，
    # 普通用户会认为排错了。name_pinyin 在写入时由模型自动生成，此处只做
    # 普通字符串比较，换数据库也不会改变顺序。
    "name": lambda: ServiceItem.name_pinyin.asc(),
    "price_asc": lambda: ServiceItem.price.asc(),
    "price_desc": lambda: ServiceItem.price.desc(),
    "popular": lambda: func.count(Appointment.id).desc(),
    "default": lambda: ServiceItem.created_at.desc(),
}


class ServiceRepository(BaseRepository):
    model = ServiceItem

    @staticmethod
    def get_by_name(name):
        if not name:
            return None
        return db.session.scalar(select(ServiceItem).where(ServiceItem.name == name.strip()))

    @staticmethod
    def name_conflict(name, exclude_id=None):
        """重名校验（编辑时排除自身）。

        原先只在新建时检查重名，编辑服务名称撞库会触发数据库唯一约束，
        最终表现为 500 —— 用户看到的是"服务器内部错误"而不是"名称已存在"。
        """
        service = ServiceRepository.get_by_name(name)
        if service is None:
            return False
        return exclude_id is None or service.id != exclude_id

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

    @staticmethod
    def counts_by_category(only_online=True):
        """分类 -> 在线服务数，一次聚合查询完成。

        原实现分类导航会按每个分类各跑一次分页查询（5 个分类 = 5 次 COUNT），
        首页/列表页多出 4 次无谓往返；改为 GROUP BY 后只查一次。
        """
        stmt = select(ServiceItem.category, func.count()).group_by(ServiceItem.category)
        if only_online:
            stmt = stmt.where(ServiceItem.status == "online")
        return {category: count for category, count in db.session.execute(stmt).all()}
