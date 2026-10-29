"""便民服务软件应用包 —— 采用 Flask 应用工厂（Application Factory）模式。

应用工厂的好处：
  1. 配置可注入：同一份代码可加载 development/testing/production 不同配置；
  2. 便于测试：单元测试可为每个用例创建一个全新的、隔离的应用实例；
  3. 延迟绑定：扩展对象在 extensions.py 中定义，在此处才与 app 绑定。

蓝图注册随实验增量推进：实验一只注册 main；实验四接入全部业务模块。
"""
from flask import Flask

from .extensions import csrf, db, login_manager


def create_app(config_name="development"):
    """创建并初始化 Flask 应用。"""
    from .config import INSTANCE_DIR, config_by_name

    app = Flask(__name__, instance_path=INSTANCE_DIR, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # 1) 绑定扩展
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # 2) 注册模型（保证 db.create_all 能发现全部数据表）
    from . import models  # noqa: F401

    # 3) 注册蓝图（按业务模块划分，体现模块化构造）
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

    # 4) 用户加载回调与模板全局变量
    _register_login(app)
    _register_template_globals(app)

    # 5) 错误页
    _register_error_handlers(app)

    return app


def _register_login(app):
    """Flask-Login 用户加载回调（会话管理的必要配置）。"""
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


def _register_template_globals(app):
    """模板全局函数：状态/分类文案与状态机查表，避免在模板中写判断逻辑。"""
    from .services.appointment_rules import next_statuses
    from .utils.constants import category_text, status_text

    app.jinja_env.globals.update(
        status_text=status_text,
        category_text=category_text,
        allowed_transitions=next_statuses,
    )


def _register_error_handlers(app):
    """统一错误提示，提升交互的可反馈性。"""
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500
