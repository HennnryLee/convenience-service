"""日志与请求追踪（工程化基础设施）。

解决的问题（可观测性）：
  1. 生产环境没有日志，出错后只能靠用户描述复现；
  2. 多个请求交织时无法把日志行对应到具体一次请求；
  3. 开发环境的 print/控制台输出无法留存，交付后无法审计。

做法：
  - 每个请求生成/透传 ``X-Request-ID``，写入日志上下文并回写到响应头；
  - 访问日志记录方法、路径、状态码与耗时，慢请求可据此定位；
  - 文件日志按大小滚动（默认 2 MB × 5 份），避免磁盘被占满；
  - 测试环境关闭文件日志、只保留 WARNING，避免污染仓库与拖慢用例。

与教材的对应：属于《软件构造》第 5 章“用户交互/可用性”之外的运行期质量保障，
也是《软件质量保证与测试》第 12 章缺陷管理中“缺陷可追踪”的基础设施。
"""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from logging.handlers import RotatingFileHandler

from flask import Flask, g, has_request_context, request

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_HANDLER_MARK = "_convenience_handler"


class RequestIdFilter(logging.Filter):
    """把当前请求的 request_id 注入每条日志记录。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = g.get("request_id", "-") if has_request_context() else "-"
        return True


def _formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _reset_handlers(logger: logging.Logger) -> None:
    """清空应用 logger 的旧 handler（同一进程反复 create_app 时避免重复输出）。

    包括 Flask 默认安装的 StreamHandler —— 否则每条日志会被打印两次。
    只操作应用自己的 logger，不影响 root/第三方库。
    """
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def configure_logging(app: Flask) -> None:
    """按配置安装控制台/文件日志，并注册请求级日志钩子。"""
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = app.logger
    logger.setLevel(level)
    # 生产环境不向 root 传播，避免被其它框架的 handler 重复打印；
    # 测试环境允许传播，pytest 的 caplog 才能捕获应用日志。
    logger.propagate = bool(app.config.get("TESTING"))

    _reset_handlers(logger)

    console = logging.StreamHandler()
    console.setFormatter(_formatter())
    console.addFilter(RequestIdFilter())
    setattr(console, _HANDLER_MARK, True)
    logger.addHandler(console)

    if app.config.get("LOG_TO_FILE"):
        log_dir = app.config.get("LOG_DIR") or os.path.join(app.instance_path, "logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=int(app.config.get("LOG_MAX_BYTES", 2 * 1024 * 1024)),
            backupCount=int(app.config.get("LOG_BACKUP_COUNT", 5)),
            encoding="utf-8",
        )
        file_handler.setFormatter(_formatter())
        file_handler.addFilter(RequestIdFilter())
        setattr(file_handler, _HANDLER_MARK, True)
        logger.addHandler(file_handler)

    _register_request_hooks(app)


def _register_request_hooks(app: Flask) -> None:
    @app.before_request
    def _start_request() -> None:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        # 只接受长度受限、字符集受限的请求 ID，防止日志注入
        g.request_id = incoming if _REQUEST_ID_PATTERN.match(incoming) else uuid.uuid4().hex[:12]
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _finish_request(response):
        request_id = g.get("request_id", "-")
        response.headers[REQUEST_ID_HEADER] = request_id
        if request.endpoint != "static":
            started = g.get("request_started_at", time.perf_counter())
            elapsed_ms = (time.perf_counter() - started) * 1000
            app.logger.info(
                "%s %s -> %s %.1fms",
                request.method,
                request.path,
                response.status_code,
                elapsed_ms,
            )
        return response
