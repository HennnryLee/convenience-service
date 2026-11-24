"""健康检查接口测试（生产部署探针）。"""
from app.extensions import db
from sqlalchemy.exc import SQLAlchemyError


def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_healthz_reports_database_failure(client, monkeypatch):
    def boom(*args, **kwargs):
        raise SQLAlchemyError("模拟数据库不可用")

    monkeypatch.setattr(db.session, "execute", boom)
    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.get_json() == {"status": "degraded", "database": "error"}
