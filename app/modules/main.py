"""首页与站点公共信息模块（蓝图 main）。

职责：站点首页、关于页；不依赖具体业务，仅做门户与导航。
"""
from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """站点首页（实验一阶段为门户骨架，后续增量接入各业务入口）。"""
    return render_template("main/index.html")


@main_bp.route("/about")
def about():
    return render_template("main/about.html")
