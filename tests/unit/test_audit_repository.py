"""审计日志仓储/服务单元测试：过滤、计数、详情格式化与显式操作者。"""
from app.models import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.audit_service import record


def test_record_with_explicit_actor_and_plain_detail(app, admin_user, normal_user):
    first = record("service.create", "service", 1, None, actor=admin_user)
    second = record("service.update", "service", 2, "纯文本详情", actor=normal_user)

    assert first.actor_username == "admin"
    assert first.detail is None
    assert second.actor_username == "zhangsan"
    assert second.detail == "纯文本详情"
    assert first.ip is None and first.request_id is None  # 无请求上下文
    assert "service.create" in repr(first)


def test_record_truncates_long_detail(app, admin_user):
    log = record("service.update", "service", 1, "x" * 2000, actor=admin_user)
    assert len(log.detail) == 1000


def test_list_logs_filters_by_action_and_actor(app, admin_user, normal_user):
    record("service.create", "service", 1, actor=admin_user)
    record("service.toggle", "service", 1, actor=admin_user)
    record("service.create", "service", 2, actor=normal_user)

    by_action = AuditLogRepository.list_logs(action="service.create")
    by_actor = AuditLogRepository.list_logs(actor_id=normal_user.id)
    combined = AuditLogRepository.list_logs(action="service.create", actor_id=admin_user.id)

    assert by_action.total == 2
    assert by_actor.total == 1
    assert by_actor.items[0].actor_id == normal_user.id
    assert combined.total == 1
    assert AuditLogRepository.count_by_action("service.create") == 2
    assert AuditLogRepository.count_by_action("no.such.action") == 0


def test_list_logs_orders_newest_first(app, admin_user):
    first = record("service.create", "service", 1, actor=admin_user)
    second = record("service.update", "service", 1, actor=admin_user)
    rows = AuditLogRepository.list_logs().items
    assert [row.id for row in rows] == [second.id, first.id]
    assert isinstance(rows[0], AuditLog)
