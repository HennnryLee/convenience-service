"""预约记录数据访问层。"""
from datetime import date

from sqlalchemy import func, select

from app.extensions import db
from app.models.appointment import Appointment

ACTIVE_STATUSES = ("pending", "confirmed")  # 计入名额占用的状态


class AppointmentRepository:
    @staticmethod
    def add(appointment, commit=True):
        db.session.add(appointment)
        if commit:
            db.session.commit()
        return appointment

    @staticmethod
    def get(appointment_id):
        return db.session.get(Appointment, appointment_id)

    @staticmethod
    def create(**fields):
        return AppointmentRepository.add(Appointment(**fields))

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
    def list_by_user(user_id, status=None, page=1, per_page=10):
        stmt = select(Appointment).where(Appointment.user_id == user_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        stmt = stmt.order_by(Appointment.appointment_date.desc(), Appointment.id.desc())
        return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def list_all(user_id=None, service_id=None, status=None, target_date=None, page=1, per_page=10):
        """后台预约管理：多条件组合查询 + 分页。"""
        stmt = select(Appointment)
        if user_id:
            stmt = stmt.where(Appointment.user_id == user_id)
        if service_id:
            stmt = stmt.where(Appointment.service_id == service_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        if target_date:
            stmt = stmt.where(Appointment.appointment_date == target_date)
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
    def save(appointment=None):
        db.session.commit()
        return appointment

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
