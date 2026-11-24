"""审计日志归档：按截止时间导出 CSV，可选删除已导出记录。

设计原则：
  - **先导出、后删除**：导出失败绝不删除任何记录；
  - 默认只导出（`remove=False`），删除必须由调用方显式开启；
  - 删除与导出在同一服务调用中完成，避免调用方忘记传参导致"导出后重复归档"；
  - 归档文件使用 UTF-8-SIG，Excel 直接打开不乱码。
"""
from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select

from app.extensions import db
from app.models.audit_log import AuditLog

COLUMNS = [
    "id",
    "created_at",
    "actor_id",
    "actor_username",
    "action",
    "target_type",
    "target_id",
    "detail",
    "ip",
    "request_id",
]


def export_logs_before(cutoff: datetime, output_path) -> int:
    """导出 created_at < cutoff 的日志，返回导出条数。"""
    stmt = (
        select(AuditLog)
        .where(AuditLog.created_at < cutoff)
        .order_by(AuditLog.id)
    )
    logs = list(db.session.scalars(stmt))

    output = Path(output_path)
    if output.parent and not output.parent.exists():
        os.makedirs(output.parent, exist_ok=True)
    with open(output, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        for log in logs:
            writer.writerow([
                log.id,
                log.created_at.isoformat(sep=" ", timespec="seconds"),
                log.actor_id,
                log.actor_username,
                log.action,
                log.target_type,
                log.target_id,
                log.detail,
                log.ip,
                log.request_id,
            ])
    return len(logs)


def archive_logs(before: datetime, output_path, remove=False) -> dict[str, int]:
    """归档截止时间之前的日志；remove=True 时删除已导出记录。

    返回 {"exported": n, "deleted": m}。
    """
    exported = export_logs_before(before, output_path)
    deleted = 0
    if remove and exported:
        db.session.execute(delete(AuditLog).where(AuditLog.created_at < before))
        db.session.commit()
        deleted = exported
    return {"exported": exported, "deleted": deleted}
