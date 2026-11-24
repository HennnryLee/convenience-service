"""审计日志功能测试：后台写操作留痕、只读页面、权限与失败降级。

覆盖点：
  - 六类管理员写操作都产生一条审计记录（actor/action/target/detail/request_id）；
  - 审计页面只读、可按动作筛选，普通用户/游客不可访问；
  - 审计表写入失败不能阻断主业务（记 ERROR 日志后继续）。
"""
from app.extensions import db
from app.models import AuditLog, ServiceItem
from app.services import audit_service
from sqlalchemy.exc import SQLAlchemyError


def _login_admin(client):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"})


def _service_form(name="审计测试服务", **overrides):
    data = {
        "name": name,
        "category": "life",
        "description": "审计测试",
        "address": "测试地址",
        "price": "10",
        "duration_minutes": "30",
        "daily_capacity": "3",
        "status": "online",
    }
    data.update(overrides)
    return data


def test_create_service_writes_audit_log(client, admin_user):
    _login_admin(client)
    client.post("/admin/services/new", data=_service_form("审计新增服务"), follow_redirects=True)

    service = db.session.query(ServiceItem).filter_by(name="审计新增服务").one()
    log = db.session.query(AuditLog).filter_by(action="service.create").one()
    assert log.actor_id == admin_user.id
    assert log.actor_username == "admin"
    assert log.target_type == "service"
    assert log.target_id == service.id
    assert "审计新增服务" in log.detail
    assert log.action_text == "新增服务"
    assert log.request_id and len(log.request_id) == 12
    assert log.ip


def test_edit_and_toggle_service_write_audit_logs(client, admin_user, service_factory):
    service = service_factory(name="审计编辑服务")
    _login_admin(client)

    client.post(
        f"/admin/services/{service.id}/edit",
        data=_service_form("审计编辑服务", price="99"),
        follow_redirects=True,
    )
    client.post(f"/admin/services/{service.id}/toggle", follow_redirects=True)

    actions = [log.action for log in db.session.query(AuditLog).order_by(AuditLog.id)]
    assert actions == ["service.update", "service.toggle"]
    assert "price" not in db.session.query(AuditLog).first().detail  # 不记录敏感字段
    assert "status=offline" in db.session.query(AuditLog).order_by(AuditLog.id.desc()).first().detail


def test_toggle_user_writes_audit_log(client, admin_user, user_factory):
    target = user_factory(username="audituser")
    _login_admin(client)
    client.post(f"/admin/users/{target.id}/toggle", follow_redirects=True)

    log = db.session.query(AuditLog).filter_by(action="user.toggle").one()
    assert log.target_id == target.id
    assert "audituser" in log.detail
    assert "active=False" in log.detail


def test_appointment_status_writes_audit_log(client, admin_user, appointment):
    _login_admin(client)
    client.post(
        f"/admin/appointments/{appointment.id}/status",
        data={"status": "confirmed"},
        follow_redirects=True,
    )

    log = db.session.query(AuditLog).filter_by(action="appointment.status").one()
    assert log.target_id == appointment.id
    assert "from=pending" in log.detail and "to=confirmed" in log.detail


def test_announcement_create_writes_audit_log(client, admin_user):
    _login_admin(client)
    client.post(
        "/admin/announcements/new",
        data={"title": "审计公告", "content": "审计公告正文", "is_published": "y"},
        follow_redirects=True,
    )

    log = db.session.query(AuditLog).filter_by(action="announcement.create").one()
    assert "审计公告" in log.detail
    assert log.target_type == "announcement"


def test_audit_page_is_read_only_and_filterable(client, admin_user, service_factory):
    service = service_factory(name="审计页面服务")
    _login_admin(client)
    client.post("/admin/services/new", data=_service_form("审计页面新增"), follow_redirects=True)
    client.post(f"/admin/services/{service.id}/toggle", follow_redirects=True)

    response = client.get("/admin/audit-logs")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "审计日志" in body
    assert "新增服务" in body and "服务上下架" in body

    filtered = client.get("/admin/audit-logs?action=service.toggle")
    filtered_body = filtered.get_data(as_text=True)
    assert "服务上下架" in filtered_body
    assert "审计页面新增" not in filtered_body  # 新增服务的详情不应出现在筛选结果中

    # 非法动作参数回退为“全部”，不应 500
    assert client.get("/admin/audit-logs?action=not-real&page=0").status_code == 200


def test_audit_page_requires_admin(client, normal_user):
    client.post("/auth/login", data={"login": "zhangsan", "password": "User@123"})
    assert client.get("/admin/audit-logs").status_code == 403


def test_audit_page_requires_login(client):
    response = client.get("/admin/audit-logs")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_audit_page_tolerates_missing_table(client, admin_user, monkeypatch):
    """旧库未迁移 audit_logs 时，页面提示运维处理，而不是 500。"""
    _login_admin(client)

    def boom(*args, **kwargs):
        raise SQLAlchemyError("no such table: audit_logs")

    monkeypatch.setattr(audit_service.AuditLogRepository, "list_logs", boom)
    response = client.get("/admin/audit-logs")
    assert response.status_code == 200
    assert "审计日志表尚未初始化" in response.get_data(as_text=True)


def test_audit_failure_does_not_block_main_action(
    client, admin_user, monkeypatch, caplog
):
    _login_admin(client)

    def boom(**kwargs):
        raise SQLAlchemyError("模拟审计表不可用")

    monkeypatch.setattr(audit_service.AuditLogRepository, "create", boom)
    response = client.post(
        "/admin/services/new", data=_service_form("审计失败仍创建"), follow_redirects=True
    )
    assert response.status_code == 200
    assert "服务已创建" in response.get_data(as_text=True)
    assert db.session.query(ServiceItem).filter_by(name="审计失败仍创建").count() == 1
    assert db.session.query(AuditLog).count() == 0
    assert "审计日志写入失败" in caplog.text
