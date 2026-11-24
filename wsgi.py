"""WSGI 入口：供 gunicorn / waitress 等生产服务器加载。

用法（Linux）：
    SECRET_KEY=... gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app

注意：生产环境必须设置 SECRET_KEY，否则应用工厂按 fail-fast 策略拒绝启动。
"""
from __future__ import annotations

import os

from app import create_app

app = create_app(os.environ.get("FLASK_CONFIG", "production"))

if __name__ == "__main__":  # pragma: no cover - 本地调试入口
    app.run(host="127.0.0.1", port=5000)
