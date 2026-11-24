"""演示数据与 Flask CLI 测试。

覆盖 `app/seed_data.py` 的幂等性、计数返回值，以及 CLI 四个命令的正常/异常路径。
这些命令是交付后运维入口，不能被“只在开发机上跑过一次”掩盖。
"""
import pytest
from app.extensions import db
from app.models import Announcement, Appointment, Feedback, ServiceItem, User
from app.seed_data import seed_demo_data


def _counts():
    return {
        "users": db.session.query(User).count(),
        "services": db.session.query(ServiceItem).count(),
        "appointments": db.session.query(Appointment).count(),
        "announcements": db.session.query(Announcement).count(),
        "feedbacks": db.session.query(Feedback).count(),
    }


def test_seed_demo_data_creates_full_dataset(app):
    created = seed_demo_data()
    assert created == {
        "users": 2,
        "services": 12,
        "announcements": 3,
        "appointments": 2,
        "feedbacks": 1,
    }
    assert _counts() == {
        "users": 2,
        "services": 12,
        "appointments": 2,
        "announcements": 3,
        "feedbacks": 1,
    }

    admin = db.session.query(User).filter_by(username="admin").one()
    zhangsan = db.session.query(User).filter_by(username="zhangsan").one()
    assert admin.role == "admin" and admin.check_password("Admin@123")
    assert zhangsan.role == "user" and zhangsan.check_password("User@123")


def test_seed_demo_data_is_idempotent(app):
    seed_demo_data()
    before = _counts()

    created = seed_demo_data()
    assert created == {
        "users": 0,
        "services": 0,
        "announcements": 0,
        "appointments": 0,
        "feedbacks": 0,
    }
    assert _counts() == before


def test_seed_keeps_existing_user_and_data(app, user_factory):
    """同名用户已存在时不得覆盖密码/角色（真实库安全）。"""
    existing = user_factory(username="admin", email="admin@example.com", role="user")
    seed_demo_data()
    refreshed = db.session.get(User, existing.id)
    assert refreshed.role == "user"
    assert refreshed.check_password("User@123")


def test_cli_init_db_and_check_db(app):
    runner = app.test_cli_runner()

    result = runner.invoke(args=["init-db"])
    assert result.exit_code == 0
    assert "表结构就绪" in result.output

    result = runner.invoke(args=["check-db"])
    assert result.exit_code == 0
    assert "数据库连接正常" in result.output
    assert "users: 0 条" in result.output


def test_cli_seed_demo_is_idempotent(app):
    runner = app.test_cli_runner()

    first = runner.invoke(args=["seed-demo"])
    assert first.exit_code == 0
    assert "users +2" in first.output
    assert "services +12" in first.output

    second = runner.invoke(args=["seed-demo"])
    assert second.exit_code == 0
    assert "users +0" in second.output


def test_cli_create_admin(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin", "boss", "boss@example.com", "--password", "Boss@1234"]
    )
    assert result.exit_code == 0
    assert "已创建" in result.output

    user = db.session.query(User).filter_by(username="boss").one()
    assert user.role == "admin"
    assert user.check_password("Boss@1234")


def test_cli_create_admin_rejects_weak_password(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin", "weak", "weak@example.com", "--password", "12345678"]
    )
    assert result.exit_code != 0
    assert "密码" in result.output


def test_cli_create_admin_rejects_duplicate(app, admin_user):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin", "admin", "other@example.com", "--password", "Admin@1234"]
    )
    assert result.exit_code != 0
    assert "已被注册" in result.output


def test_cli_check_db_reports_missing_tables(app):
    db.drop_all()
    runner = app.test_cli_runner()
    result = runner.invoke(args=["check-db"])
    assert result.exit_code != 0
    assert "缺少数据表" in result.output


def test_seed_rolls_back_when_database_write_fails(app, monkeypatch):
    """写入失败时必须回滚，不能留下"一半演示数据"（事务原子性）。"""
    from app.extensions import db as extensions_db

    def boom():
        raise RuntimeError("模拟数据库写入失败")

    monkeypatch.setattr(extensions_db.session, "commit", boom)
    with pytest.raises(RuntimeError):
        seed_demo_data()
    monkeypatch.undo()

    assert db.session.query(User).count() == 0
    assert db.session.query(ServiceItem).count() == 0
