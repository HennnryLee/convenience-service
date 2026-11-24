"""审计日志数据访问层。"""
from sqlalchemy import select

from app.extensions import db
from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository):
    model = AuditLog

    @classmethod
    def create(cls, **fields):
        return cls.add(AuditLog(**fields))

    @staticmethod
    def list_logs(action=None, actor_id=None, page=1, per_page=20):
        """后台审计列表：按时间倒序，可按动作/操作者过滤。"""
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def count_by_action(action):
        from sqlalchemy import func

        return db.session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.action == action)
        )
