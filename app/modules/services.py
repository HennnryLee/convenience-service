"""服务查询模块（蓝图 services）：分类浏览、关键词搜索、详情查看。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.forms import ServiceSearchForm
from app.services.search_service import search_service_page
from app.services.service_catalog import get_categories_with_count, get_service_detail
from app.utils.pagination import parse_page

services_bp = Blueprint("services", __name__)


@services_bp.route("/")
def list_services():
    form = ServiceSearchForm(request.args, meta={"csrf": False})
    outcome = search_service_page(
        keyword=form.keyword.data,
        category=form.category.data or None,
        sort=form.sort.data or "default",
        page=parse_page(request.args.get("page")),
    )
    if outcome.message:
        category = "warning" if outcome.pagination is None else "info"
        flash(outcome.message, category)

    return render_template(
        "services/list.html",
        form=form,
        pagination=outcome.pagination,
        keyword=outcome.keyword,
        categories=get_categories_with_count(),
    )


@services_bp.route("/<int:service_id>")
def detail(service_id):
    service_detail = get_service_detail(service_id)
    if service_detail is None:
        flash("该服务不存在或已下架。", "warning")
        return redirect(url_for("services.list_services"))
    return render_template("services/detail.html", **service_detail)
