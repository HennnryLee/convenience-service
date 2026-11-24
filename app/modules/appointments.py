"""在线预约模块（蓝图 appointments）：提交预约、查看我的预约、取消预约。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.config import Config
from app.forms import AppointmentForm
from app.repositories import AppointmentRepository, ServiceRepository
from app.services.appointment_service import (
    auto_complete_due,
    cancel_appointment,
    create_appointment,
)
from app.utils.constants import APPOINTMENT_STATUS_TEXT
from app.utils.decorators import consumer_only
from app.utils.pagination import parse_choice, parse_page

appointments_bp = Blueprint("appointments", __name__)


@appointments_bp.route("/create/<int:service_id>", methods=["GET", "POST"])
@login_required
def create(service_id):
    # 最小权限：管理员职责是管理与发布，不参与前台预约业务（DEF-009）
    if getattr(current_user, "role", None) == "admin":
        flash("管理员账号用于后台管理，不可提交预约，请使用普通用户账号。", "warning")
        return redirect(url_for("services.detail", service_id=service_id))

    service = ServiceRepository.get(service_id)
    if service is None or not service.is_online:
        flash("该服务不存在或已下架，请选择其它服务。", "warning")
        return redirect(url_for("services.list_services"))

    form = AppointmentForm()
    if form.validate_on_submit():
        appointment, errors = create_appointment(
            user=current_user,
            service_id=service.id,
            appointment_date=form.appointment_date.data,
            time_slot=form.time_slot.data,
            contact_name=form.contact_name.data,
            contact_phone=form.contact_phone.data,
            remark=form.remark.data,
        )
        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template("appointments/create.html", form=form, service=service)
        flash(f"预约提交成功，编号为 #{appointment.id}，请等待确认。", "success")
        return redirect(url_for("appointments.my_appointments"))

    return render_template("appointments/create.html", form=form, service=service)


@appointments_bp.route("/mine")
@login_required
@consumer_only
def my_appointments():
    # 展示前先按时段自动办结：服务时间结束的「已确认」预约自动变为「已完成」（DEF-011）
    # 只办结本人的预约，避免一次页面访问触发全站写操作
    auto_complete_due(user_id=current_user.id)
    status = parse_choice(request.args.get("status"), APPOINTMENT_STATUS_TEXT)
    page = parse_page(request.args.get("page"))
    pagination = AppointmentRepository.list_by_user(
        current_user.id, status=status, page=page, per_page=Config.USER_ITEMS_PER_PAGE
    )
    return render_template(
        "appointments/mine.html", pagination=pagination, status=status
    )


@appointments_bp.route("/<int:appointment_id>/cancel", methods=["POST"])
@login_required
@consumer_only
def cancel(appointment_id):
    appointment = AppointmentRepository.get(appointment_id)
    ok, message = cancel_appointment(appointment, current_user)
    flash(message, "success" if ok else "danger")
    return redirect(url_for("appointments.my_appointments"))
