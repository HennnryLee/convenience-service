"""审计日志服务：把管理员写操作记录为可追溯的审计事件。

调用约定：
  - 在业务写操作**成功提交之后**调用（不要在事务中调用），
    这样审计失败只会回滚审计本身，不会把已完成的业务写操作一起回滚；
  - detail 只放非敏感信息（名称、状态、变更字段），绝不记录密码/令牌；
  - 没有请求上下文时（CLI/测试直接调用）actor 用显式传入的 user 或 "system"。
"""
from __future__ import annotations

from flask import current_app, g, has_request_context, request
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.repositories.audit_log_repository import AuditLogRepository

_MAX_DETAIL_LENGTH = 1000


def _format_detail(detail) -> str | None:
    if not detail:
        return None
    if isinstance(detail, dict):
        text = "；".join(f"{key}={value}" for key, value in detail.items())
    else:
        text = str(detail)
    return text[:_MAX_DETAIL_LENGTH]


def record(action, target_type=None, target_id=None, detail=None, actor=None):
    """写入一条审计日志；失败时只记录错误，不影响主业务。

    返回 AuditLog 实例；写入失败返回 None。
    """
    if actor is None and has_request_context() and current_user.is_authenticated:
        actor = current_user

    try:
        log = AuditLogRepository.create(
            actor_id=getattr(actor, "id", None),
            actor_username=getattr(actor, "username", None) or "system",
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=_format_detail(detail),
            ip=(request.remote_addr if has_request_context() else None),
            request_id=(g.get("request_id") if has_request_context() else None),
        )
        return log
    except SQLAlchemyError:
        # 审计表不存在/写入失败不能阻断管理员的主操作；回滚审计事务后记 ERROR。
        db.session.rollback()
        current_app.logger.exception(
            "审计日志写入失败：action=%s target=%s#%s", action, target_type, target_id
        )
        return None
