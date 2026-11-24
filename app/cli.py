"""Flask CLI 命令（替代把运维逻辑堆在 run.py 里的做法）。

用法：
    flask --app "app:create_app()" init-db
    flask --app "app:create_app()" seed-demo
    flask --app "app:create_app()" create-admin <username> <email>
    flask --app "app:create_app()" check-db

设计要点：
  - CLI 与 Web 请求共用应用工厂与配置，避免“脚本连的库和网站不是同一个”；
  - 破坏性操作不提供默认入口（清库仍需 run.py --force-reset 显式确认）；
  - 命令只做编排，业务规则复用 services / repositories，避免脚本成为第二套实现。
"""
from __future__ import annotations

import click
from flask import Flask
from flask.cli import with_appcontext
from sqlalchemy import func, inspect, select

from app.extensions import db
from app.models import Announcement, Appointment, Feedback, ServiceItem, User
from app.seed_data import seed_demo_data
from app.services.auth_service import register_user, validate_registration


def _counts() -> dict[str, int]:
    return {
        "users": db.session.scalar(select(func.count()).select_from(User)),
        "services": db.session.scalar(select(func.count()).select_from(ServiceItem)),
        "appointments": db.session.scalar(select(func.count()).select_from(Appointment)),
        "announcements": db.session.scalar(select(func.count()).select_from(Announcement)),
        "feedbacks": db.session.scalar(select(func.count()).select_from(Feedback)),
    }


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    """建表（幂等，绝不删除已有数据）。"""
    db.create_all()
    click.echo("[OK] 数据库表结构就绪（未删除已有数据）")


@click.command("seed-demo")
@with_appcontext
def seed_demo_command() -> None:
    """写入演示数据（幂等，同名记录自动跳过）。"""
    created = seed_demo_data()
    summary = "、".join(f"{name} +{count}" for name, count in created.items())
    click.echo(f"[OK] 演示数据已就绪（本次新增：{summary}）")


@click.command("create-admin")
@click.argument("username")
@click.argument("email")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True,
              help="管理员密码（8-20 位，含字母与数字）")
@with_appcontext
def create_admin_command(username: str, email: str, password: str) -> None:
    """创建管理员账号（复用注册校验，避免脚本绕过密码策略）。"""
    errors = validate_registration(username, email, password, password)
    if errors:
        raise click.ClickException("；".join(errors.values()))
    user = register_user(username, email, password, role="admin")
    click.echo(f"[OK] 管理员 {user.username} 已创建（id={user.id}）")


@click.command("check-db")
@with_appcontext
def check_db_command() -> None:
    """自检：连接、表结构、各表行数。"""
    tables = set(inspect(db.engine).get_table_names())
    expected = {"users", "services", "appointments", "announcements", "feedbacks"}
    missing = sorted(expected - tables)
    if missing:
        raise click.ClickException(f"缺少数据表：{', '.join(missing)}，请先执行 init-db")

    click.echo("[OK] 数据库连接正常，表结构完整")
    for name, count in _counts().items():
        click.echo(f"  {name}: {count} 条")


def register_cli(app: Flask) -> None:
    """把命令注册到应用实例（create_app 调用）。"""
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_demo_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(check_db_command)
