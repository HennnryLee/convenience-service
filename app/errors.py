"""统一错误处理（HTTP 错误页 + 服务端异常日志）。

设计原则（与《软件构造》4.3 防御性编程一致）：
  - 对**用户**：任何错误都给出统一、可理解的页面与下一步操作，不泄露堆栈；
  - 对**维护者**：5xx 必须带 request_id 写入日志，便于把用户反馈对应到日志行；
  - 对**安全**：CSRF 失败按 400 处理并记录来源路径，不把令牌内容写进日志。
"""
from __future__ import annotations

from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import (
    BadRequest,
    Forbidden,
    MethodNotAllowed,
    NotFound,
    RequestEntityTooLarge,
)


def _render_error(code: int, title: str, message: str):
    return (
        render_template(
            "errors/error.html",
            code=code,
            title=title,
            message=message,
        ),
        code,
    )


def register_error_handlers(app: Flask) -> None:
    """注册常用 HTTP 错误与 CSRF 异常处理器。"""

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):  # noqa: ANN001 - Flask 回调签名固定
        app.logger.warning(
            "CSRF 校验失败：path=%s ip=%s reason=%s",
            request.path,
            request.remote_addr,
            error.description,
        )
        return _render_error(
            400,
            "请求校验失败",
            "表单已过期或校验失败，请刷新页面后重新提交。",
        )

    @app.errorhandler(BadRequest)
    def handle_bad_request(error):  # noqa: ANN001
        return _render_error(400, "请求无法处理", "请求参数不完整或格式不正确，请返回后重试。")

    @app.errorhandler(Forbidden)
    def handle_forbidden(error):  # noqa: ANN001
        return _render_error(403, "无访问权限", "你没有访问该资源的权限，请使用具备权限的账号登录。")

    @app.errorhandler(NotFound)
    def handle_not_found(error):  # noqa: ANN001
        return _render_error(404, "页面不存在", "你访问的地址不存在，请返回首页继续浏览。")

    @app.errorhandler(MethodNotAllowed)
    def handle_method_not_allowed(error):  # noqa: ANN001
        return _render_error(405, "请求方法不允许", "该地址不支持当前请求方式，请从页面上的入口操作。")

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(error):  # noqa: ANN001
        return _render_error(413, "请求内容过大", "提交的内容超过系统允许的大小，请精简后重试。")

    @app.errorhandler(500)
    def handle_server_error(error):  # noqa: ANN001
        original = getattr(error, "original_exception", None)
        app.logger.error(
            "服务器内部错误：path=%s method=%s detail=%s",
            request.path,
            request.method,
            original or error,
            exc_info=original is not None,
        )
        return _render_error(500, "服务器内部错误", "系统出现异常，我们已记录该问题，请稍后重试。")
