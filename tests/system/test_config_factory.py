"""应用工厂与配置测试：生产密钥 fail-fast、环境变量选择、配置隔离。"""
import pytest
from app import create_app
from app.config import DEFAULT_SECRET_KEY, ProductionConfig, TestingConfig


def test_production_refuses_default_secret_key(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", DEFAULT_SECRET_KEY)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


def test_production_accepts_explicit_secret_and_enables_secure_cookies(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "x" * 32)
    monkeypatch.setattr(ProductionConfig, "LOG_TO_FILE", False)
    app = create_app("production")
    assert app.config["DEBUG"] is False
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["REMEMBER_COOKIE_SECURE"] is True


def test_config_name_can_come_from_environment(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "testing")
    app = create_app()
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == TestingConfig.SQLALCHEMY_DATABASE_URI


def test_testing_config_isolated_from_real_database():
    app = create_app("testing")
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert app.config["WTF_CSRF_ENABLED"] is False
    assert app.config["LOG_TO_FILE"] is False
