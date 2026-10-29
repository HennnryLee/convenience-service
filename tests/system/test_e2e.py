"""端到端（E2E）系统集成测试：覆盖完整业务主干流程。

流程：注册 → 登录 → 服务查询 → 在线预约 → 我的预约 →
      管理员确认 → 管理员完成 → 用户评价 → 我的评价 → 退出。
"""
from datetime import date, timedelta

from app.extensions import db
from app.models import Appointment, Feedback, ServiceItem, User

PASSWORD = "User@123"


def _register_and_login(client, username, email):
    client.post(
        "/auth/register",
        data={"username": username, "email": email, "phone": "13800138001",
              "real_name": "端到端测试用户", "password": PASSWORD, "confirm": PASSWORD},
        follow_redirects=True,
    )
    client.post("/auth/login", data={"login": username, "password": PASSWORD},
                follow_redirects=True)


def test_full_business_journey(client, admin_user, service):
    # 1) 注册 + 登录
    _register_and_login(client, "e2euser", "e2e@example.com")
    user = User.query.filter_by(username="e2euser").first()
    assert user is not None and user.role == "user"

    # 2) 服务查询
    resp = client.get("/services/?keyword=" + "身份证")
    assert resp.status_code == 200 and service.name.encode() in resp.data

    # 3) 在线预约
    day = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = client.post(
        f"/appointments/create/{service.id}",
        data={"appointment_date": day, "time_slot": "09:00-10:00",
              "contact_name": "端到端", "contact_phone": "13800138001", "remark": "E2E"},
        follow_redirects=True,
    )
    assert "预约提交成功".encode() in resp.data
    appointment = Appointment.query.filter_by(user_id=user.id).first()
    assert appointment is not None and appointment.status == "pending"

    # 4) 我的预约可见
    resp = client.get("/appointments/mine")
    assert appointment.service.name.encode() in resp.data

    # 5) 后台：管理员确认 → 完成
    client.get("/auth/logout")
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"},
                follow_redirects=True)
    assert client.get("/admin/").status_code == 200

    client.post(f"/admin/appointments/{appointment.id}/status",
                data={"status": "confirmed"}, follow_redirects=True)
    assert Appointment.query.get(appointment.id).status == "confirmed"

    client.post(f"/admin/appointments/{appointment.id}/status",
                data={"status": "completed"}, follow_redirects=True)
    assert Appointment.query.get(appointment.id).status == "completed"

    # 6) 用户评价
    client.get("/auth/logout")
    client.post("/auth/login", data={"login": "e2euser", "password": PASSWORD},
                follow_redirects=True)
    resp = client.get("/feedback/create")
    assert resp.status_code == 200
    resp = client.post(
        "/feedback/create",
        data={"appointment_id": appointment.id, "rating": "5", "content": "端到端流程体验良好"},
        follow_redirects=True,
    )
    assert "感谢你的评价".encode() in resp.data
    feedback = Feedback.query.filter_by(appointment_id=appointment.id).first()
    assert feedback is not None and feedback.rating == 5

    # 7) 我的评价可见，且服务详情页展示评分
    assert feedback.content.encode() in client.get("/feedback/mine").data
    assert "5 星".encode() in client.get(f"/services/{service.id}").data

    # 8) 退出后会话失效
    client.get("/auth/logout")
    assert client.get("/appointments/mine").status_code == 302


def test_offline_service_cannot_be_booked(client, admin_user, service):
    client.post("/auth/login", data={"login": "admin", "password": "Admin@123"},
                follow_redirects=True)
    client.post(f"/admin/services/{service.id}/toggle", follow_redirects=True)
    assert ServiceItem.query.get(service.id).status == "offline"

    client.get("/auth/logout")
    _register_and_login(client, "e2e2", "e2e2@example.com")
    resp = client.get(f"/appointments/create/{service.id}", follow_redirects=True)
    assert "已下架".encode() in resp.data or service.name.encode() not in resp.data
