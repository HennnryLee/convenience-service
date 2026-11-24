"""公告资讯模块（蓝图 announcements）：列表、详情、关键词搜索。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.forms import AnnouncementSearchForm
from app.services.announcement_service import (
    get_published_announcement,
    search_announcements_page,
)
from app.utils.pagination import parse_page

announcements_bp = Blueprint("announcements", __name__)


@announcements_bp.route("/")
def list_announcements():
    form = AnnouncementSearchForm(request.args, meta={"csrf": False})
    outcome = search_announcements_page(
        keyword=form.keyword.data,
        page=parse_page(request.args.get("page")),
    )
    if outcome.message:
        category = "warning" if outcome.pagination is None else "info"
        flash(outcome.message, category)
    return render_template(
        "announcements/list.html",
        form=form,
        pagination=outcome.pagination,
        keyword=outcome.keyword,
    )


@announcements_bp.route("/<int:announcement_id>")
def detail(announcement_id):
    announcement = get_published_announcement(announcement_id)
    if announcement is None:
        flash("该公告不存在或未发布。", "warning")
        return redirect(url_for("announcements.list_announcements"))
    return render_template("announcements/detail.html", announcement=announcement)
