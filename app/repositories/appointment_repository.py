"""预约记录数据访问层。"""
from datetime import date

from sqlalchemy import func, select

from app.extensions import db
from app.models.appointment import Appointment
from app.repositories.base import BaseRepository

ACTIVE_STATUSES = ("pending", "confirmed")  # 计入名额占用的状态


class AppointmentRepository(BaseRepository):
    model = Appointment

    @classmethod
    def create(cls, **fields):
        return cls.add(Appointment(**fields))

    @staticmethod
    def count_active(service_id, appointment_date, time_slot):
        """统计该服务该时段已被占用的名额（已取消的不计）。"""
        return db.session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.service_id == service_id,
                Appointment.appointment_date == appointment_date,
                Appointment.time_slot == time_slot,
                Appointment.status.in_(ACTIVE_STATUSES),
            )
        )

    @staticmethod
    def has_active_duplicate(user_id, service_id, appointment_date, time_slot):
        """同一用户是否已预约过同一服务的同一时段（已取消的不算）。"""
        return (
            db.session.scalar(
                select(func.count())
                .select_from(Appointment)
                .where(
                    Appointment.user_id == user_id,
                    Appointment.service_id == service_id,
                    Appointment.appointment_date == appointment_date,
                    Appointment.time_slot == time_slot,
                    Appointment.status.in_(ACTIVE_STATUSES),
                )
            )
            > 0
        )

    @staticmethod
    def _apply_filters(stmt, filters):
        """表驱动过滤：把"条件 -> 字段"映射成字典，替代连续 if（重构：以表驱动替换条件表达式）。"""
        field_map = {
            "user_id": Appointment.user_id,
            "service_id": Appointment.service_id,
            "status": Appointment.status,
            "appointment_date": Appointment.appointment_date,
        }
        for key, value in filters.items():
            if value is not None and key in field_map:
                stmt = stmt.where(field_map[key] == value)
        return stmt

    @classmethod
    def list_by_user(cls, user_id, status=None, page=1, per_page=10):
        stmt = select(Appointment).where(Appointment.user_id == user_id)
        stmt = cls._apply_filters(stmt, {"status": status})
        stmt = stmt.order_by(Appointment.appointment_date.desc(), Appointment.id.desc())
        return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    @classmethod
    def list_all(cls, user_id=None, service_id=None, status=None, target_date=None,
                 page=1, per_page=10):
        """后台预约管理：多条件组合查询 + 分页。"""
        stmt = cls._apply_filters(
            select(Appointment),
            {
                "user_id": user_id,
                "service_id": service_id,
                "status": status,
                "appointment_date": target_date,
            },
        )
        stmt = stmt.order_by(Appointment.appointment_date.desc(), Appointment.id.desc())
        return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def list_by_service_date(service_id, appointment_date):
        stmt = select(Appointment).where(
            Appointment.service_id == service_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_(ACTIVE_STATUSES),
        )
        return list(db.session.scalars(stmt))

    @staticmethod
    def count_by_status(status=None):
        stmt = select(func.count()).select_from(Appointment)
        if status:
            stmt = stmt.where(Appointment.status == status)
        return db.session.scalar(stmt)

    @staticmethod
    def count_by_date(target_date: date):
        return db.session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.appointment_date == target_date)
        )
