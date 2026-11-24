"""配置模块：集中管理系统配置，体现"配置与代码分离"的模块化思想。

运行环境通过 create_app(config_name) 选择，便于开发、测试、交付三种环境隔离：
  - development：开发环境，使用 instance/app.db（SQLite），开启调试与 CSRF
  - testing    ：测试环境，使用内存数据库，关闭 CSRF（便于自动化接口测试）
  - production ：交付环境，强制要求 SECRET_KEY，可通过 DATABASE_URL 切换到 MySQL 8.0

安全相关配置（2026-11-24 工程化改进）：
  - 会话 Cookie 统一 HttpOnly + SameSite=Lax，生产环境追加 Secure；
  - 记住登录 Cookie 同样受保护；
  - 生产环境若仍使用默认 SECRET_KEY，应用工厂会拒绝启动（fail fast）。
"""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

# 确保实例目录存在（SQLite 数据库文件存放位置），避免首次运行时"unable to open database file"
os.makedirs(INSTANCE_DIR, exist_ok=True)

DEFAULT_SECRET_KEY = "dev-only-secret-key-change-me"

# 数据库 URI 默认使用 SQLite；若设置环境变量 DATABASE_URL（如
# mysql+pymysql://user:password@localhost:3306/convenience?charset=utf8mb4）
# 则自动切换到 MySQL，业务代码无需任何改动（见 docs/10-部署与运行说明.md）
DEFAULT_SQLITE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "app.db").replace("\\", "/")


class Config:
    """所有环境的公共配置。"""

    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URI)

    # 交互相关（重构：以常量替换视图中的魔法数字）
    ITEMS_PER_PAGE = 9              # 服务列表页分页大小
    USER_ITEMS_PER_PAGE = 10        # 个人中心（我的预约/我的评价）分页大小
    ADMIN_ITEMS_PER_PAGE = 10       # 后台管理列表分页大小
    MAX_SEARCH_KEYWORD = 50         # 服务/公告搜索关键词最大长度（边界值分析用）
    REMEMBER_COOKIE_DURATION = 3600  # 登录会话有效期（秒）

    # 业务规则参数（集中放置，避免在代码中散落"魔法数字"）
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 20

    # ---- 会话与 Cookie 安全（防御会话劫持 / CSRF 辅助）----
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # 请求体上限：本站只有文本表单，1 MB 足以覆盖，避免超大请求耗尽内存
    MAX_CONTENT_LENGTH = 1024 * 1024

    # ---- 日志（app/logging.py）----
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_DIR = os.path.join(INSTANCE_DIR, "logs")
    LOG_TO_FILE = True
    LOG_MAX_BYTES = 2 * 1024 * 1024
    LOG_BACKUP_COUNT = 5


class DevelopmentConfig(Config):
    DEBUG = True
    WTF_CSRF_ENABLED = True


class TestingConfig(Config):
    """测试环境：内存数据库 + 关闭 CSRF，保证测试可重复执行且互不污染。"""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SERVER_NAME = "localhost.localdomain"
    LOG_LEVEL = "WARNING"
    LOG_TO_FILE = False


class ProductionConfig(Config):
    DEBUG = False
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
