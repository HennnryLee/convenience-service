"""Gunicorn 生产配置（Linux）。

用法：
    SECRET_KEY=... FLASK_CONFIG=production DATABASE_URL=... \
    gunicorn -c deploy/gunicorn.conf.py wsgi:app

说明：
  - 默认只监听 127.0.0.1:8000，由 Nginx 终止 TLS 并反向代理；
  - 不开启 preload_app：应用工厂/数据库/日志在各自 worker 内初始化，避免 fork 后共享句柄；
  - 若仍使用 SQLite，多 worker 写操作会竞争文件锁，生产应切换 MySQL（见 docs/16）。
"""
import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.environ.get("WEB_WORKERS", str(min(multiprocessing.cpu_count() * 2 + 1, 8))))
threads = int(os.environ.get("WEB_THREADS", "2"))
worker_class = "gthread"

timeout = int(os.environ.get("WEB_TIMEOUT", "60"))
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

preload_app = False
