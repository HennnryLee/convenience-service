"""领域对象：反馈评价（Feedback）。对应模块：反馈评价。"""
from datetime import datetime

from app.extensions import db


class Feedback(db.Model):
    """评价实体。

    不变量：
        - rating ∈ [1,5]（CHECK 约束）；
        - appointment_id 唯一 —— 一条预约最多被评价一次（业务规则 + 唯一索引双重保证）。
    """

    __tablename__ = "feedbacks"
    __table_args__ = (
        db.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=True, unique=True
    )
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now())

    user = db.relationship("User", back_populates="feedbacks")
    service = db.relationship("ServiceItem", back_populates="feedbacks")
    appointment = db.relationship("Appointment", back_populates="feedback")

    @property
    def rating_text(self):
        from app.utils.constants import RATING_TEXT

        return RATING_TEXT.get(self.rating, "")

    def __repr__(self):
        return f"<Feedback {self.id} rating={self.rating}>"
