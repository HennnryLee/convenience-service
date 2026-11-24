"""首页与站点公共信息模块（蓝图 main）。

职责：站点首页、关于页；不依赖具体业务，仅做门户与导航。
数据编排已下沉到 ``home_service``，视图只负责渲染。
"""
from flask import Blueprint, redirect, render_template, url_for

from app.services.home_service import get_home_data

main_bp = Blueprint("main", __name__)


@main_bp.route("/favicon.ico")
def favicon():
    """站点图标：浏览器自动请求 /favicon.ico 时重定向到 SVG 图标，避免 404。"""
    return redirect(url_for("static", filename="favicon.svg"))


@main_bp.route("/")
def index():
    """站点首页：展示热门服务入口与最新公告。"""
    return render_template("main/index.html", **get_home_data())


@main_bp.route("/about")
def about():
    return render_template("main/about.html")
