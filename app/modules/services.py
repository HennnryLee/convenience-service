"""服务查询模块（蓝图 services）：分类浏览、关键词搜索、详情查看。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.config import Config
from app.forms import ServiceSearchForm
from app.repositories import ServiceRepository
from app.services.service_catalog import get_categories_with_count, get_service_detail, search_services

services_bp = Blueprint("services", __name__)


@services_bp.route("/")
def list_services():
    form = ServiceSearchForm(request.args, meta={"csrf": False})
    keyword = (form.keyword.data or "").strip()
    category = form.category.data or None
    sort = form.sort.data or "default"
    page = request.args.get("page", 1, type=int)

    if len(keyword) > Config.MAX_SEARCH_KEYWORD:
        flash(f"搜索关键词不能超过 {Config.MAX_SEARCH_KEYWORD} 个字符。", "warning")
        pagination = None
    else:
        pagination = search_services(keyword=keyword, category=category, sort=sort, page=page)
        if pagination.total == 0:
            flash("没有找到匹配的服务，请尝试其它关键词或分类。", "info")

    return render_template(
        "services/list.html",
        form=form,
        pagination=pagination,
        keyword=keyword,
        categories=get_categories_with_count(),
    )


@services_bp.route("/<int:service_id>")
def detail(service_id):
    detail = get_service_detail(service_id)
    if detail is None:
        flash("该服务不存在或已下架。", "warning")
        return redirect(url_for("services.list_services"))
    return render_template("services/detail.html", **detail)
