"""视图装饰器：权限控制（管理员校验）。"""
from functools import wraps

from flask import abort
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
