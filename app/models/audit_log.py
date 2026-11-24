"""审计日志（管理员写操作留痕）。

设计目标（对应《软件质量保证与测试》第 12 章缺陷管理中的“可追溯性”，
以及《软件构造》第 8 章数据库应用中的“事务与日志”思想）：
  - **只追加**：不提供修改/删除入口，避免审计记录被业务代码覆盖；
  - **冗余 actor_username**：用户被删除/改名后，历史记录仍能回答“当时是谁做的”；
  - **记录 request_id**：可与 app/logging.py 的访问日志按同一 ID 关联；
  - **失败不阻断主业务**：审计写入异常时回滚审计事务并记 ERROR 日志，
    不能让“记日志失败”导致管理员的正常操作失败（见 services/audit_service.py）。

注意：本表是运行期支撑表，不属于领域模型的核心实体；
它只在后台管理动作后写入，不参与预约/评价等业务规则。
"""
from datetime import datetime

from app.extensions import db
from app.utils.constants import audit_action_text


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (
        db.Index("ix_audit_created_at", "created_at"),
        db.Index("ix_audit_action", "action"),
        db.Index("ix_audit_actor", "actor_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_username = db.Column(db.String(20), nullable=False, default="system")
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(30))
    target_id = db.Column(db.Integer)
    detail = db.Column(db.Text)
    ip = db.Column(db.String(45))
    request_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now())

    actor = db.relationship("User", foreign_keys=[actor_id])

    @property
    def action_text(self):
        return audit_action_text(self.action)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.actor_username}>"
