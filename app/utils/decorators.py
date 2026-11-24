"""视图装饰器：权限控制（管理员校验 / 消费者页面校验）。"""
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(view_func):
    """要求当前登录用户具备管理员角色，否则返回 403。

    前置条件：已通过 @login_required 保证已登录（装饰器顺序：login_required 在外层）。
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapper


def consumer_only(view_func):
    """仅允许消费者（普通用户）访问的页面：管理员一律引导回后台管理。

    设计动机（DEF-010）：管理员是服务/平台提供方，职责是管理与发布，
    「我的预约」「我的评价」「提交评价」属于消费者侧功能。此前仅拦截了
    "提交预约" 这一个动作，管理员仍能进入这些页面，造成角色职责混淆。

    与 admin_required 的区别：这里是「引导」而非「拒绝」（302 + 提示，不是 403），
    因为管理员误点旧链接属于导航问题，不是越权攻击。
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_admin:
            flash("管理员账号用于后台管理与服务发布，不参与预约、评价等消费者操作。", "info")
            return redirect(url_for("admin.dashboard"))
        return view_func(*args, **kwargs)

    return wrapper
