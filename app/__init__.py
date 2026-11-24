"""便民服务软件应用包 —— 采用 Flask 应用工厂（Application Factory）模式。

应用工厂的好处：
  1. 配置可注入：同一份代码可加载 development/testing/production 不同配置；
  2. 便于测试：单元测试可为每个用例创建一个全新的、隔离的应用实例；
  3. 延迟绑定：扩展对象在 extensions.py 中定义，在此处才与 app 绑定。

初始化顺序（2026-11-24 工程化改进）：
    配置校验 → 扩展绑定 → 蓝图注册 → 登录/模板 → 日志与安全 → 错误页 → CLI
其中日志必须先于错误处理注册，5xx 日志才带得上 request_id；安全头独立成模块，
便于系统测试单独验证，不与业务代码耦合。
"""
from __future__ import annotations

import os

from flask import Flask

from .extensions import csrf, db, login_manager, migrate


def create_app(config_name=None):
    """创建并初始化 Flask 应用。

    参数：
        config_name: development / testing / production，默认读环境变量 FLASK_CONFIG。
    """
    from .config import DEFAULT_SECRET_KEY, INSTANCE_DIR, config_by_name

    config_name = config_name or os.environ.get("FLASK_CONFIG", "development")
    config_class = config_by_name.get(config_name, config_by_name["default"])

    # 生产环境 fail fast：默认密钥意味着会话可被伪造，不能带病上线
    if config_name == "production" and config_class.SECRET_KEY == DEFAULT_SECRET_KEY:
        raise RuntimeError(
            "生产环境必须通过环境变量 SECRET_KEY 设置随机密钥，"
            "不能使用默认开发密钥启动。"
        )

    app = Flask(__name__, instance_path=INSTANCE_DIR, instance_relative_config=True)
    app.config.from_object(config_class)
    app.json.ensure_ascii = False

    _init_extensions(app)
    _register_blueprints(app)
    _register_login(app)
    _register_template_globals(app)
    _init_observability(app)
    return app


def _init_extensions(app):
    """绑定扩展并导入模型，保证 db.create_all 能发现全部数据表。"""
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    from . import models  # noqa: F401


def _register_blueprints(app):
    """按业务模块注册蓝图，体现模块化构造。"""
    from .modules.admin import admin_bp
    from .modules.announcements import announcements_bp
    from .modules.appointments import appointments_bp
    from .modules.auth import auth_bp
    from .modules.feedback import feedback_bp
    from .modules.main import main_bp
    from .modules.services import services_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(appointments_bp, url_prefix="/appointments")
    app.register_blueprint(announcements_bp, url_prefix="/announcements")
    app.register_blueprint(feedback_bp, url_prefix="/feedback")
    app.register_blueprint(admin_bp, url_prefix="/admin")


def _init_observability(app):
    """日志、安全响应头、统一错误页与运维命令。"""
    from .cli import register_cli
    from .errors import register_error_handlers
    from .logging import configure_logging
    from .security import init_security

    configure_logging(app)
    init_security(app)
    register_error_handlers(app)
    register_cli(app)


def _register_login(app):
    """Flask-Login 用户加载回调（会话管理的必要配置）。

    安全细节：被管理员禁用的账号即使浏览器还持有旧会话，也必须在下次请求时
    失效（返回 None 等价于匿名），否则「禁用」只对新登录生效。
    """
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            return None
        user = db.session.get(User, user_id_int)
        if user is None or not user.is_active:
            return None
        return user


def _register_template_globals(app):
    """模板全局函数：状态/分类文案与状态机查表，避免在模板中写判断逻辑。"""
    from .services.appointment_rules import next_statuses
    from .utils.constants import category_text, status_text

    app.jinja_env.globals.update(
        status_text=status_text,
        category_text=category_text,
        allowed_transitions=next_statuses,
    )
