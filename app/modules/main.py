"""首页与站点公共信息模块（蓝图 main）。

职责：站点首页、关于页、健康检查；不依赖具体业务，仅做门户与导航。
数据编排已下沉到 ``home_service``，视图只负责渲染。
"""
from flask import Blueprint, current_app, jsonify, redirect, render_template, url_for
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.services.home_service import get_home_data

main_bp = Blueprint("main", __name__)


@main_bp.route("/healthz")
def healthz():
    """健康检查：供 Nginx/负载均衡/监控探测，不返回任何业务数据。"""
    try:
        db.session.execute(select(1))
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("健康检查失败：数据库不可用")
        return jsonify(status="degraded", database="error"), 503
    return jsonify(status="ok", database="ok")


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
