"""反馈评价数据访问层。"""
from sqlalchemy import func, select

from app.extensions import db
from app.models.feedback import Feedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository):
    model = Feedback

    @classmethod
    def create(cls, user_id, service_id, appointment_id, rating, content=None):
        return cls.add(
            Feedback(
                user_id=user_id,
                service_id=service_id,
                appointment_id=appointment_id,
                rating=rating,
                content=content,
            )
        )

    @staticmethod
    def get_by_appointment(appointment_id):
        return db.session.scalar(
            select(Feedback).where(Feedback.appointment_id == appointment_id)
        )

    @staticmethod
    def list_by_user(user_id, page=1, per_page=10):
        stmt = (
            select(Feedback)
            .where(Feedback.user_id == user_id)
            .order_by(Feedback.created_at.desc())
        )
        return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def list_by_service(service_id, limit=10):
        stmt = (
            select(Feedback)
            .where(Feedback.service_id == service_id)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
        )
        return list(db.session.scalars(stmt))

    @staticmethod
    def average_rating(service_id):
        return db.session.scalar(
            select(func.avg(Feedback.rating)).where(Feedback.service_id == service_id)
        )
