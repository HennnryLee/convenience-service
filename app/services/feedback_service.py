"""反馈评价服务：评价资格判定与评价提交。"""
from app.repositories.feedback_repository import FeedbackRepository


def can_review(user, appointment):
    """评价资格判定。

    规则：仅当预约属于本人、状态为"已完成"、且尚未评价过时才允许。
    返回 (bool, 原因)。
    """
    if appointment is None:
        return False, "预约记录不存在。"
    if appointment.user_id != user.id:
        return False, "只能评价本人的预约。"
    if appointment.status != "completed":
        return False, "仅已完成的预约可以评价。"
    if FeedbackRepository.get_by_appointment(appointment.id):
        return False, "该预约已评价过，不能重复提交。"
    return True, ""


def create_feedback(user, appointment, rating, content=None):
    """提交评价。前置条件：已通过 can_review。"""
    ok, reason = can_review(user, appointment)
    if not ok:
        return None, reason
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return None, "评分必须为 1-5 之间的整数。"
    feedback = FeedbackRepository.create(
        user_id=user.id,
        service_id=appointment.service_id,
        appointment_id=appointment.id,
        rating=rating,
        content=(content or "").strip() or None,
    )
    return feedback, ""


def list_reviewable_appointments(user):
    """列出当前用户可评价的预约（已完成且未评价）。"""
    return [
        appt
        for appt in user.appointments
        if appt.status == "completed" and not FeedbackRepository.get_by_appointment(appt.id)
    ]
