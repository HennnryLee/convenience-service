"""反馈评价模块（蓝图 feedback）：提交评价、查看历史评价。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.config import Config

from app.forms import FeedbackForm
from app.repositories import AppointmentRepository, FeedbackRepository
from app.services.feedback_service import create_feedback, list_reviewable_appointments

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    reviewable = list_reviewable_appointments(current_user)
    if not reviewable:
        flash("你当前没有可评价的预约（仅「已完成」且未评价的预约可评价）。", "info")
        return redirect(url_for("feedback.my_feedback"))

    form = FeedbackForm()
    form.appointment_id.choices = [(a.id, f"#{a.id} · {a.service.name} · {a.appointment_date}") for a in reviewable]

    if form.validate_on_submit():
        appointment = AppointmentRepository.get(form.appointment_id.data)
        feedback, reason = create_feedback(
            current_user, appointment, form.rating.data, form.content.data
        )
        if feedback is None:
            flash(reason, "danger")
            return render_template("feedback/create.html", form=form)
        flash("感谢你的评价！", "success")
        return redirect(url_for("feedback.my_feedback"))

    return render_template("feedback/create.html", form=form)


@feedback_bp.route("/mine")
@login_required
def my_feedback():
    page = request.args.get("page", 1, type=int)
    pagination = FeedbackRepository.list_by_user(
        current_user.id, page=page, per_page=Config.USER_ITEMS_PER_PAGE
    )
    return render_template("feedback/mine.html", pagination=pagination)
