"""扩展（第三方组件）统一管理模块。

把 db / login_manager / csrf 等扩展对象定义在独立模块中，
避免"扩展实例 ↔ 应用实例"循环依赖（应用工厂模式的常见陷阱）。
"""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# 未登录用户访问受保护资源时重定向到登录页，并给出中文提示
login_manager.login_view = "auth.login"
login_manager.login_message = "请先登录后再访问该页面。"
login_manager.login_message_category = "warning"
