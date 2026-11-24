"""后台概览的应用服务：集中统计口径，视图只负责渲染。"""
from __future__ import annotations

from datetime import date

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.service_repository import ServiceRepository
from app.repositories.user_repository import UserRepository


def get_dashboard_stats(today=None):
    """后台首页统计（今日 = 可注入日期，避免测试依赖系统时钟）。"""
    today = today or date.today()
    return {
        # 「注册用户」是消费者口径，不含管理员账号；管理员不是平台的服务对象。
        "users": UserRepository.count(role="user"),
        "services": ServiceRepository.count_by_status("online"),
        "appointments": AppointmentRepository.count_by_status(),
        "pending": AppointmentRepository.count_by_status("pending"),
        "today": AppointmentRepository.count_by_date(today),
        "feedbacks": FeedbackRepository.count_all(),
    }
