"""首页与站点公共信息模块（蓝图 main）。

职责：站点首页、关于页；不依赖具体业务，仅做门户与导航。
"""
from flask import Blueprint, redirect, render_template, url_for

from app.repositories import AnnouncementRepository, ServiceRepository

main_bp = Blueprint("main", __name__)


@main_bp.route("/favicon.ico")
def favicon():
    """站点图标：浏览器自动请求 /favicon.ico 时重定向到 SVG 图标，避免 404。"""
    return redirect(url_for("static", filename="favicon.svg"))


@main_bp.route("/")
def index():
    """站点首页：展示热门服务入口与最新公告。"""
    hot_services = ServiceRepository.list_online(limit=3)
    announcements = AnnouncementRepository.latest(limit=5)
    return render_template(
        "main/index.html", hot_services=hot_services, announcements=announcements
    )


@main_bp.route("/about")
def about():
    return render_template("main/about.html")
