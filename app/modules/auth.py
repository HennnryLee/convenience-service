"""用户管理模块（蓝图 auth）：注册、登录、退出、个人信息修改。"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import LoginForm, ProfileForm, RegistrationForm
from app.services import auth_service

auth_bp = Blueprint("auth", __name__)


def _is_safe_next(target):
    """只允许站内相对路径跳转，防止开放重定向漏洞。"""
    return bool(target) and target.startswith("/") and not target.startswith("//")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        auth_service.register_user(
            username=form.username.data.strip(),
            email=form.email.data.strip(),
            password=form.password.data,
            phone=(form.phone.data or "").strip() or None,
            real_name=(form.real_name.data or "").strip() or None,
        )
        flash("注册成功，请使用新账号登录。", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = auth_service.authenticate(form.login.data.strip(), form.password.data)
        if user is None:
            # 统一提示，不区分"用户不存在"与"密码错误"，避免账号枚举
            flash("用户名或密码错误。", "danger")
            return render_template("auth/login.html", form=form)
        if not user.is_active:
            flash("账号已被禁用，请联系管理员。", "warning")
            return render_template("auth/login.html", form=form)
        login_user(user, remember=form.remember.data)
        flash(f"欢迎回来，{user.username}！", "success")
        next_url = request.args.get("next")
        return redirect(next_url if _is_safe_next(next_url) else url_for("main.index"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已安全退出登录。", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(original_email=current_user.email, obj=current_user)
    if form.validate_on_submit():
        auth_service.update_profile(
            current_user,
            email=form.email.data.strip(),
            phone=(form.phone.data or "").strip() or None,
            real_name=(form.real_name.data or "").strip() or None,
        )
        db.session.commit()
        flash("个人信息已更新。", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)
