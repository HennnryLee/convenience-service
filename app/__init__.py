"""便民服务软件应用包 —— 采用 Flask 应用工厂（Application Factory）模式。

应用工厂的好处：
  1. 配置可注入：同一份代码可加载 development/testing/production 不同配置；
  2. 便于测试：单元测试可为每个用例创建一个全新的、隔离的应用实例；
  3. 延迟绑定：扩展对象在 extensions.py 中定义，在此处才与 app 绑定。

【实验一】当前仅注册 main 蓝图（首页骨架），
后续实验按增量方式在此追加蓝图注册（见 Git 提交历史）。
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
    csrf.init_app(app)
    # 注：login_manager（会话与登录状态）在实验四"用户交互构造"增量接入，
    #     届时需同时注册 user_loader 回调（Flask-Login 强制要求）。

    # 2) 注册模型（保证 db.create_all 能发现全部数据表）
    from . import models  # noqa: F401

    # 3) 注册蓝图（按业务模块划分，体现模块化构造）
    from .modules.main import main_bp

    app.register_blueprint(main_bp)

    # 3) 错误页
    _register_error_handlers(app)

    return app


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
