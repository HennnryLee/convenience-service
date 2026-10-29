"""配置模块：集中管理系统配置，体现"配置与代码分离"的模块化思想。

运行环境通过 create_app(config_name) 选择，便于开发、测试、交付三种环境隔离：
  - development：开发环境，使用 instance/app.db（SQLite）
  - testing    ：测试环境，使用内存数据库，关闭 CSRF（便于自动化接口测试）
  - production ：交付环境，可通过环境变量 DATABASE_URL 切换到 MySQL 8.0
"""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

# 数据库 URI 默认使用 SQLite；若设置环境变量 DATABASE_URL（如
# mysql+pymysql://user:password@localhost:3306/convenience?charset=utf8mb4）
# 则自动切换到 MySQL，业务代码无需任何改动（见 docs/05-部署与运行说明.md）
DEFAULT_SQLITE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "app.db").replace("\\", "/")


class Config:
    """所有环境的公共配置。"""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URI)

    # 交互相关
    ITEMS_PER_PAGE = 9              # 列表页分页大小
    MAX_SEARCH_KEYWORD = 50         # 服务/公告搜索关键词最大长度（边界值分析用）
    REMEMBER_COOKIE_DURATION = 3600  # 登录会话有效期（秒）

    # 业务规则参数（集中放置，避免在代码中散落"魔法数字"）
    APPOINTMENT_MAX_DAYS_AHEAD = 30  # 最多可预约未来 30 天
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 20


class DevelopmentConfig(Config):
    DEBUG = True
    WTF_CSRF_ENABLED = True


class TestingConfig(Config):
    """测试环境：内存数据库 + 关闭 CSRF，保证测试可重复执行且互不污染。"""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SERVER_NAME = "localhost.localdomain"


class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_ENABLED = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
