"""审计日志归档测试：导出 CSV、默认不删除、显式删除只影响截止日期前记录。"""
import csv
from datetime import datetime

from app.extensions import db
from app.models import AuditLog
from app.services.audit_archive import archive_logs, export_logs_before


def _make_log(action, when):
    log = AuditLog(
        actor_username="admin",
        action=action,
        target_type="service",
        target_id=1,
        detail="测试",
        created_at=when,
    )
    db.session.add(log)
    db.session.commit()
    return log


def test_export_only_keeps_records(app, tmp_path):
    old = _make_log("service.create", datetime(2025, 12, 31, 23, 59))
    new = _make_log("service.update", datetime(2026, 1, 2, 0, 0))
    output = tmp_path / "audit.csv"

    result = archive_logs(datetime(2026, 1, 1), output, remove=False)
    assert result == {"exported": 1, "deleted": 0}
    with open(output, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    assert rows[0][0] == "id" and rows[0][4] == "action"
    assert len(rows) == 2
    assert "service.create" in rows[1]
    assert db.session.get(AuditLog, old.id) is not None
    assert db.session.get(AuditLog, new.id) is not None


def test_delete_removes_only_exported_records(app, tmp_path):
    old = _make_log("service.create", datetime(2025, 12, 31, 23, 59))
    new = _make_log("service.update", datetime(2026, 1, 2, 0, 0))
    output = tmp_path / "audit.csv"

    result = archive_logs(datetime(2026, 1, 1), output, remove=True)
    assert result == {"exported": 1, "deleted": 1}
    assert db.session.get(AuditLog, old.id) is None
    assert db.session.get(AuditLog, new.id) is not None


def test_export_empty_table_writes_header(app, tmp_path):
    output = tmp_path / "nested" / "empty.csv"
    assert export_logs_before(datetime(2026, 1, 1), output) == 0
    with open(output, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == 1
