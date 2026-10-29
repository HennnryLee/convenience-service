"""公告资讯模块（蓝图 announcements）：列表、详情、关键词搜索。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.config import Config
from app.forms import AnnouncementSearchForm
from app.repositories import AnnouncementRepository

announcements_bp = Blueprint("announcements", __name__)


@announcements_bp.route("/")
def list_announcements():
    form = AnnouncementSearchForm(request.args, meta={"csrf": False})
    keyword = (form.keyword.data or "").strip()
    page = request.args.get("page", 1, type=int)

    if len(keyword) > Config.MAX_SEARCH_KEYWORD:
        flash(f"搜索关键词不能超过 {Config.MAX_SEARCH_KEYWORD} 个字符。", "warning")
        pagination = None
    else:
        pagination = AnnouncementRepository.search(keyword=keyword or None, page=page)
        if pagination.total == 0:
            flash("没有找到相关公告。", "info")
    return render_template("announcements/list.html", form=form, pagination=pagination, keyword=keyword)


@announcements_bp.route("/<int:announcement_id>")
def detail(announcement_id):
    announcement = AnnouncementRepository.get(announcement_id)
    if announcement is None or not announcement.is_published:
        flash("该公告不存在或未发布。", "warning")
        return redirect(url_for("announcements.list_announcements"))
    return render_template("announcements/detail.html", announcement=announcement)
