"""集成测试：验证模块之间的接口协作与数据传递。

集成策略：**自底向上（Bottom-Up）**
选择理由：系统的数据访问层（Repository）与业务规则层（services）已完成单元测试，
先确保底层稳定，再逐层向上集成到表现层（蓝图），
可以用真实数据库替代桩模块，且缺陷定位容易（先验的是底层已通过测试）。

四个关键集成点：
  I-1 用户管理模块 → 在线预约模块：传递登录状态（会话/用户身份）
  I-2 服务查询模块 → 在线预约模块：传递服务项目信息
  I-3 在线预约模块 → 后台管理模块：提交预约记录供后台处理
  I-4 后台管理模块 → 反馈评价模块：预约完成后触发评价邀请（资格开放）
"""
from datetime import date, timedelta

from app.extensions import db
from app.models import Appointment, Feedback, User
from app.repositories import AppointmentRepository, FeedbackRepository
from app.services.feedback_service import list_reviewable_appointments

DAY = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")


def _login(client, username, password):
    return client.post("/auth/login", data={"login": username, "password": password},
                       follow_redirects=True)


def _book(client, service_id, slot="09:00-10:00"):
    return client.post(
        f"/appointments/create/{service_id}",
        data={"appointment_date": DAY, "time_slot": slot,
              "contact_name": "集成测试", "contact_phone": "13800138000"},
        follow_redirects=True,
    )


# ------------------------------------------------------------------ I-1
def test_i1_login_state_delivered_to_appointment_module(client, normal_user, service):
    """I-1：登录后会话中的用户身份被预约模块正确接收（写入正确的 user_id）。"""
    _login(client, "zhangsan", "User@123")
    resp = _book(client, service.id)
    assert resp.status_code == 200
    appt = Appointment.query.first()
    assert appt is not None and appt.user_id == normal_user.id


def test_i1_without_login_appointment_module_rejects(client, service):
    """I-1 异常：未登录时预约模块拒绝访问并回传重定向到登录页。"""
    resp = client.get(f"/appointments/create/{service.id}")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
    assert Appointment.query.count() == 0


def test_i1_session_not_shared_between_users(client, normal_user, service):
    """I-1 异常：A 用户预约后退出，B 用户不应看到 A 的预约。"""
    _login(client, "zhangsan", "User@123")
    _book(client, service.id)
    client.get("/auth/logout")

    other = User(username="otheruser", email="other@example.com")
    other.set_password("User@123")
    db.session.add(other)
    db.session.commit()
    _login(client, "otheruser", "User@123")
    body = client.get("/appointments/mine").get_data(as_text=True)
    assert "集成测试".encode().decode() not in body
    assert AppointmentRepository.list_by_user(other.id).total == 0


# ------------------------------------------------------------------ I-2
def test_i2_service_info_delivered_to_appointment(client, normal_user, service):
    """I-2：从服务详情跳转预约时，service_id 被正确传递并落库。"""
    _login(client, "zhangsan", "User@123")
    resp = client.get(f"/services/{service.id}")
    assert resp.status_code == 200
    _book(client, service.id)
    appt = Appointment.query.first()
    assert appt.service_id == service.id
    assert appt.service.name == service.name


def test_i2_offline_service_not_delivered(client, admin_user, service):
    """I-2 异常：已下架服务的 id 被传入预约模块时，请求被拒绝且不写库。"""
    _login(client, "admin", "Admin@123")
    client.post(f"/admin/services/{service.id}/toggle", follow_redirects=True)
    client.get("/auth/logout")

    user = User(username="user002", email="u2@example.com")
    user.set_password("User@123")
    db.session.add(user)
    db.session.commit()
    _login(client, "user002", "User@123")
    resp = client.get(f"/appointments/create/{service.id}", follow_redirects=True)
    assert "已下架".encode() in resp.data
    assert Appointment.query.count() == 0


def test_i2_invalid_service_id_rejected(client, normal_user):
    """I-2 异常：传入不存在的服务 id → 不写库并给出提示。"""
    _login(client, "zhangsan", "User@123")
    resp = client.get("/appointments/create/9999", follow_redirects=True)
    assert "不存在".encode() in resp.data
    assert Appointment.query.count() == 0


# ------------------------------------------------------------------ I-3
def test_i3_appointment_record_visible_in_admin(client, normal_user, admin_user, service):
    """I-3：用户提交的预约能被后台管理模块查询到（数据经数据库传递）。"""
    _login(client, "zhangsan", "User@123")
    _book(client, service.id)
    assert AppointmentRepository.count_by_status("pending") == 1

    client.get("/auth/logout")
    _login(client, "admin", "Admin@123")
    body = client.get("/admin/appointments").get_data(as_text=True)
    assert service.name in body
    assert "待确认" in body


def test_i3_admin_status_change_reflected_to_user(client, normal_user, admin_user, service,
                                                  appointment):
    """I-3：后台推进状态后，用户在"我的预约"中看到最新状态。"""
    _login(client, "admin", "Admin@123")
    client.post(f"/admin/appointments/{appointment.id}/status",
                data={"status": "confirmed"}, follow_redirects=True)
    assert Appointment.query.get(appointment.id).status == "confirmed"

    client.get("/auth/logout")
    _login(client, "zhangsan", "User@123")
    body = client.get("/appointments/mine").get_data(as_text=True)
    assert "已确认" in body


def test_i3_illegal_status_change_rejected(client, admin_user, appointment):
    """I-3 异常：非法状态流转被拒绝，数据库状态保持不变。"""
    _login(client, "admin", "Admin@123")
    client.post(f"/admin/appointments/{appointment.id}/status",
                data={"status": "completed"}, follow_redirects=True)
    assert Appointment.query.get(appointment.id).status == "pending"  # 未变更


def test_i3_missing_parameters_rejected(client, admin_user, appointment):
    """I-3 异常：参数缺失的后台提交不改变数据。"""
    _login(client, "admin", "Admin@123")
    resp = client.post(f"/admin/appointments/{appointment.id}/status", data={})
    assert resp.status_code in (200, 302)
    assert Appointment.query.get(appointment.id).status == "pending"


# ------------------------------------------------------------------ I-4
def test_i4_completed_appointment_enables_feedback(client, normal_user, admin_user, service):
    """I-4：后台把预约置为"已完成"后，反馈评价模块对该预约开放。"""
    _login(client, "zhangsan", "User@123")
    _book(client, service.id)
    appt = Appointment.query.first()
    assert list_reviewable_appointments(normal_user) == []   # 未完成 → 不可评价

    client.get("/auth/logout")
    _login(client, "admin", "Admin@123")
    client.post(f"/admin/appointments/{appt.id}/status",
                data={"status": "confirmed"}, follow_redirects=True)
    client.post(f"/admin/appointments/{appt.id}/status",
                data={"status": "completed"}, follow_redirects=True)

    client.get("/auth/logout")
    _login(client, "zhangsan", "User@123")
    assert len(list_reviewable_appointments(normal_user)) == 1  # 触发评价邀请


def test_i4_feedback_bound_to_appointment_and_service(client, normal_user, admin_user, service):
    """I-4：评价记录正确关联预约与服务，可在服务详情中看到。"""
    _login(client, "zhangsan", "User@123")
    _book(client, service.id)
    appt = Appointment.query.first()
    appt.change_status("completed")
    db.session.commit()

    resp = client.post("/feedback/create",
                       data={"appointment_id": appt.id, "rating": "4", "content": "集成测试评价"},
                       follow_redirects=True)
    assert "感谢你的评价".encode() in resp.data
    fb = FeedbackRepository.get_by_appointment(appt.id)
    assert fb.service_id == service.id and fb.rating == 4
    assert "4 星".encode() in client.get(f"/services/{service.id}").data


def test_i4_duplicate_feedback_rejected(client, normal_user, service, appointment):
    """I-4 异常：同一预约重复评价被拒绝，评价总数不变。"""
    appointment.change_status("completed")
    db.session.commit()
    _login(client, "zhangsan", "User@123")
    client.post("/feedback/create", data={"appointment_id": appointment.id,
                                          "rating": "5", "content": "第一次"},
                follow_redirects=True)
    resp = client.post("/feedback/create", data={"appointment_id": appointment.id,
                                                 "rating": "3", "content": "第二次"},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert Feedback.query.count() == 1
