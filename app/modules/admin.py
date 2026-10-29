"""后台管理模块（蓝图 admin）：服务管理、用户管理、预约管理、公告发布。"""
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.config import Config
from app.forms import AnnouncementForm, AppointmentStatusForm, ServiceForm, UserSearchForm
from app.repositories import (
    AnnouncementRepository,
    AppointmentRepository,
    FeedbackRepository,
    ServiceRepository,
    UserRepository,
)
from app.services.appointment_service import change_status
from app.utils.decorators import admin_required

admin_bp = Blueprint("admin", __name__)

PER_PAGE = Config.ADMIN_ITEMS_PER_PAGE


def _build_service_payload(form):
    """重构：提炼函数（Extract Method）—— 把表单到实体的字段映射独立出来，
    使 edit_service 视图函数只关注流程控制，长度与圈复杂度同时下降。"""
    return dict(
        name=form.name.data.strip(),
        category=form.category.data,
        description=(form.description.data or "").strip(),
        address=(form.address.data or "").strip(),
        price=form.price.data or 0,
        duration_minutes=form.duration_minutes.data or 30,
        daily_capacity=form.daily_capacity.data or 5,
        status=form.status.data,
    )


@admin_bp.before_request
@login_required
@admin_required
def protect():
    """统一守卫：后台所有视图都要求"已登录 + 管理员"。"""
    return None


@admin_bp.route("/")
def dashboard():
    stats = {
        "users": UserRepository.count(),
        "services": ServiceRepository.count_by_status("online"),
        "appointments": AppointmentRepository.count_by_status(),
        "pending": AppointmentRepository.count_by_status("pending"),
        "today": AppointmentRepository.count_by_date(date.today()),
        "feedbacks": FeedbackRepository.count_all(),
    }
    return render_template("admin/dashboard.html", stats=stats)


# ---------------------------------------------------------------- 服务管理
@admin_bp.route("/services")
def services():
    page = request.args.get("page", 1, type=int)
    pagination = ServiceRepository.search(only_online=False, page=page, per_page=PER_PAGE)
    return render_template("admin/services.html", pagination=pagination)


@admin_bp.route("/services/new", methods=["GET", "POST"])
@admin_bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
def edit_service(service_id=None):
    service = ServiceRepository.get(service_id) if service_id else None
    if service_id and service is None:
        flash("服务不存在。", "warning")
        return redirect(url_for("admin.services"))

    form = ServiceForm(obj=service)
    if form.validate_on_submit():
        payload = _build_service_payload(form)
        if service:
            ServiceRepository.update(service, **payload)
            flash("服务信息已更新。", "success")
        else:
            if ServiceRepository.get_by_name(payload["name"]):
                flash("同名服务已存在。", "danger")
                return render_template("admin/service_form.html", form=form, service=service)
            ServiceRepository.create(**payload)
            flash("服务已创建。", "success")
        return redirect(url_for("admin.services"))
    return render_template("admin/service_form.html", form=form, service=service)


@admin_bp.route("/services/<int:service_id>/toggle", methods=["POST"])
def toggle_service(service_id):
    service = ServiceRepository.get(service_id)
    if service is None:
        flash("服务不存在。", "warning")
        return redirect(url_for("admin.services"))
    new_status = "offline" if service.is_online else "online"
    ServiceRepository.set_status(service, new_status)
    flash(f"服务已{'下架' if new_status == 'offline' else '上架'}。", "success")
    return redirect(url_for("admin.services"))


# ---------------------------------------------------------------- 用户管理
@admin_bp.route("/users")
def users():
    form = UserSearchForm(request.args, meta={"csrf": False})
    keyword = (form.keyword.data or "").strip() or None
    page = request.args.get("page", 1, type=int)
    pagination = UserRepository.search(keyword=keyword, page=page, per_page=PER_PAGE)
    return render_template("admin/users.html", pagination=pagination, form=form)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
def toggle_user(user_id):
    user = UserRepository.get(user_id)
    if user is None:
        flash("用户不存在。", "warning")
    elif user.id == current_user.id:
        flash("不能禁用当前登录的管理员账号。", "danger")
    else:
        UserRepository.set_active(user, not user.is_active)
        flash(f"用户 {user.username} 已{'启用' if user.is_active else '禁用'}。", "success")
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------- 预约管理
@admin_bp.route("/appointments")
def appointments():
    status = request.args.get("status") or None
    page = request.args.get("page", 1, type=int)
    pagination = AppointmentRepository.list_all(status=status, page=page, per_page=PER_PAGE)
    return render_template("admin/appointments.html", pagination=pagination, status=status)


@admin_bp.route("/appointments/<int:appointment_id>/status", methods=["POST"])
def update_appointment_status(appointment_id):
    appointment = AppointmentRepository.get(appointment_id)
    form = AppointmentStatusForm()
    if appointment is None:
        flash("预约不存在。", "warning")
    elif form.validate_on_submit():
        ok, message = change_status(appointment, form.status.data)
        flash(message, "success" if ok else "danger")
    else:
        flash("提交信息无效，请重试。", "danger")
    return redirect(url_for("admin.appointments"))


# ---------------------------------------------------------------- 公告发布
@admin_bp.route("/announcements/new", methods=["GET", "POST"])
def new_announcement():
    form = AnnouncementForm()
    if form.validate_on_submit():
        AnnouncementRepository.create(
            title=form.title.data.strip(),
            content=form.content.data.strip(),
            author_id=current_user.id,
            is_published=bool(form.is_published.data),
        )
        flash("公告已发布。", "success")
        return redirect(url_for("announcements.list_announcements"))
    return render_template("admin/announcement_form.html", form=form)
