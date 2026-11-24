"""Web 安全响应头与会话防护（纵深防御）。

对应《软件质量保证与测试》系统测试中的安全性测试：
  - 点击劫持：X-Frame-Options + CSP frame-ancestors；
  - MIME 嗅探：X-Content-Type-Options；
  - XSS 兜底：CSP 限制脚本/样式来源（模板已由 Jinja2 自动转义，CSP 是第二道防线）；
  - 信息泄露：Referrer-Policy、Permissions-Policy；
  - 传输安全：HTTPS 下追加 HSTS（仅生产环境、仅安全连接）。

Cookie 策略在 config.py 中集中声明，本模块只负责响应头。
"""
from __future__ import annotations

from flask import Flask, request

# 静态资源全部由本站提供，模板中不写内联 style/script，因此可用较严格的 CSP。
# 若后续引入外部 CDN，请只把对应域名加入白名单，不要整体放开。
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self'; "
    "script-src 'self'; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    # 现代浏览器已弃用该过滤器，显式关闭以避免旧版浏览器把它当 XSS 检测器误伤
    "X-XSS-Protection": "0",
}


def init_security(app: Flask) -> None:
    """注册安全响应头；生产环境 HTTPS 请求追加 HSTS。"""

    @app.after_request
    def _add_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if app.config.get("SESSION_COOKIE_SECURE") and request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
