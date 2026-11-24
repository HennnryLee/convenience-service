"""后台管理模块（蓝图 admin）：服务管理、用户管理、预约管理、公告发布。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app.config import Config
from app.extensions import db
from app.forms import (
    AdminResetPasswordForm,
    AnnouncementForm,
    AppointmentStatusForm,
    ServiceForm,
    UserSearchForm,
)
from app.repositories import (
    AnnouncementRepository,
    AppointmentRepository,
    AuditLogRepository,
    FeedbackRepository,
    ServiceRepository,
    UserRepository,
)
from app.services import audit_service, auth_service
from app.services.appointment_service import auto_complete_due, change_status
from app.services.dashboard_service import get_dashboard_stats
from app.utils.constants import APPOINTMENT_STATUS_TEXT, AUDIT_ACTION_TEXT
from app.utils.decorators import admin_required
from app.utils.pagination import parse_choice, parse_page

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
    return render_template("admin/dashboard.html", stats=get_dashboard_stats())


# ---------------------------------------------------------------- 服务管理
@admin_bp.route("/services")
def services():
    page = parse_page(request.args.get("page"))
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
        exclude_id = service.id if service else None
        if ServiceRepository.name_conflict(payload["name"], exclude_id=exclude_id):
            flash("同名服务已存在。", "danger")
            return render_template("admin/service_form.html", form=form, service=service)
        if service:
            ServiceRepository.update(service, **payload)
            audit_service.record(
                "service.update", "service", service.id,
                {"name": payload["name"], "category": payload["category"]},
            )
            flash("服务信息已更新。", "success")
        else:
            created = ServiceRepository.create(**payload)
            audit_service.record(
                "service.create", "service", created.id,
                {"name": payload["name"], "category": payload["category"]},
            )
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
    audit_service.record("service.toggle", "service", service.id, {"status": new_status})
    flash(f"服务已{'下架' if new_status == 'offline' else '上架'}。", "success")
    return redirect(url_for("admin.services"))


# ---------------------------------------------------------------- 用户管理
@admin_bp.route("/users")
def users():
    form = UserSearchForm(request.args, meta={"csrf": False})
    keyword = (form.keyword.data or "").strip() or None
    page = parse_page(request.args.get("page"))
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
        audit_service.record(
            "user.toggle", "user", user.id,
            {"username": user.username, "active": user.is_active},
        )
        flash(f"用户 {user.username} 已{'启用' if user.is_active else '禁用'}。", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
def reset_password(user_id):
    """管理员为普通用户设置临时密码（课程级找回密码，不发送邮件）。"""
    user = UserRepository.get(user_id)
    if user is None:
        flash("用户不存在。", "warning")
        return redirect(url_for("admin.users"))
    if user.role != "user":
        flash("仅支持重置普通用户的密码；管理员请通过个人中心或 CLI 维护。", "warning")
        return redirect(url_for("admin.users"))

    form = AdminResetPasswordForm(target_username=user.username)
    if form.validate_on_submit():
        ok, message = auth_service.reset_user_password(user, form.password.data)
        if ok:
            audit_service.record(
                "user.reset_password", "user", user.id,
                {"username": user.username},
            )
            flash(message, "success")
            return redirect(url_for("admin.users"))
        flash(message, "danger")
    return render_template("admin/reset_password.html", form=form, target_user=user)


# ---------------------------------------------------------------- 预约管理
@admin_bp.route("/appointments")
def appointments():
    # 展示前先自动办结：服务时段已结束的「已确认」预约自动变为「已完成」（DEF-011）
    completed_count = auto_complete_due()
    if completed_count:
        flash(f"已按服务时段自动办结 {completed_count} 条到期预约（已确认 → 已完成）。", "info")
    status = parse_choice(request.args.get("status"), APPOINTMENT_STATUS_TEXT)
    page = parse_page(request.args.get("page"))
    pagination = AppointmentRepository.list_all(status=status, page=page, per_page=PER_PAGE)
    return render_template("admin/appointments.html", pagination=pagination, status=status)


@admin_bp.route("/appointments/<int:appointment_id>/status", methods=["POST"])
def update_appointment_status(appointment_id):
    appointment = AppointmentRepository.get(appointment_id)
    form = AppointmentStatusForm()
    if appointment is None:
        flash("预约不存在。", "warning")
    elif form.validate_on_submit():
        old_status = appointment.status
        ok, message = change_status(appointment, form.status.data)
        if ok:
            audit_service.record(
                "appointment.status", "appointment", appointment.id,
                {"from": old_status, "to": appointment.status},
            )
        flash(message, "success" if ok else "danger")
    else:
        flash("提交信息无效，请重试。", "danger")
    return redirect(url_for("admin.appointments"))


# ---------------------------------------------------------------- 评价查看（只读）
@admin_bp.route("/feedbacks")
def feedbacks():
    """管理员以服务提供方身份查看消费者的反馈，页面不提供任何提交/修改入口。"""
    page = parse_page(request.args.get("page"))
    pagination = FeedbackRepository.list_all(page=page, per_page=PER_PAGE)
    return render_template("admin/feedbacks.html", pagination=pagination)


# ---------------------------------------------------------------- 审计日志（只读）
@admin_bp.route("/audit-logs")
def audit_logs():
    """管理员查看审计日志；只读页面，不提供修改/删除入口。"""
    action = parse_choice(request.args.get("action"), AUDIT_ACTION_TEXT)
    page = parse_page(request.args.get("page"))
    try:
        pagination = AuditLogRepository.list_logs(action=action, page=page, per_page=PER_PAGE)
    except SQLAlchemyError:
        # 旧库尚未执行 audit_logs 迁移时，给运维可理解的提示，而不是 500。
        db.session.rollback()
        flash("审计日志表尚未初始化，请先执行数据库迁移（见 docs/16）。", "warning")
        pagination = None
    return render_template(
        "admin/audit_logs.html",
        pagination=pagination,
        action=action,
        actions=AUDIT_ACTION_TEXT,
    )


# ---------------------------------------------------------------- 公告发布
@admin_bp.route("/announcements/new", methods=["GET", "POST"])
def new_announcement():
    form = AnnouncementForm()
    if form.validate_on_submit():
        announcement = AnnouncementRepository.create(
            title=form.title.data.strip(),
            content=form.content.data.strip(),
            author_id=current_user.id,
            is_published=bool(form.is_published.data),
        )
        audit_service.record(
            "announcement.create", "announcement", announcement.id,
            {"title": announcement.title},
        )
        flash("公告已发布。", "success")
        return redirect(url_for("announcements.list_announcements"))
    return render_template("admin/announcement_form.html", form=form)
