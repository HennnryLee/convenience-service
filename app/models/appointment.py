"""领域对象：预约记录（Appointment）。

对应模块：在线预约 / 后台管理（预约处理）。
状态流转规则见 app.utils.constants.APPOINTMENT_TRANSITIONS（表驱动）。
"""
from datetime import datetime

from app.extensions import db


class Appointment(db.Model):
    """预约记录实体。

    属性不变量：
        - user_id、service_id 必须指向存在的记录（外键约束）；
        - status ∈ {pending, confirmed, completed, cancelled}（CHECK 约束）；
        - 同一用户在同一服务的同一日期时段最多存在一条"未取消"的预约
          （由服务层 AppointmentContext.has_duplicate 判定，并在数据库层建索引加速）。
    """

    __tablename__ = "appointments"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'confirmed', 'completed', 'cancelled')", name="ck_appt_status"
        ),
        db.Index("ix_appt_slot", "service_id", "appointment_date", "time_slot"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)
    contact_name = db.Column(db.String(30), nullable=False)
    contact_phone = db.Column(db.String(11), nullable=False)
    remark = db.Column(db.Text)
    status = db.Column(db.String(10), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now())
    updated_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(), onupdate=lambda: datetime.now()
    )

    user = db.relationship("User", back_populates="appointments")
    service = db.relationship("ServiceItem", back_populates="appointments")
    feedback = db.relationship("Feedback", back_populates="appointment", uselist=False)

    # ------------------------------------------------------------------ 行为
    @property
    def is_cancelled(self):
        return self.status == "cancelled"

    @property
    def status_text(self):
        from app.utils.constants import status_text

        return status_text(self.status)

    def change_status(self, new_status):
        """修改状态（前置条件由调用方用 can_transition 校验；此处只做赋值与时间戳更新）。

        后置条件：状态更新，updated_at 刷新；不变量：状态值始终合法。
        """
        self.status = new_status
        self.updated_at = datetime.now()

    def __repr__(self):
        return f"<Appointment {self.id} {self.appointment_date} {self.time_slot} {self.status}>"
