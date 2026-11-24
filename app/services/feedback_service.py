"""反馈评价服务：评价资格判定与评价提交。"""
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.utils.constants import MAX_RATING, MIN_RATING


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
    """提交评价。前置条件：已通过 can_review。

    纵深防御（DEF-010）：视图层已用 consumer_only 把管理员挡在评价页面之外，
    服务层再拦一次，保证绕过视图直接调用写入口也无法以管理员身份评价。
    管理员是服务提供方，评价是消费者侧的权利，二者不可混用。
    """
    if getattr(user, "role", None) == "admin":
        return None, "管理员账号用于后台管理与服务发布，不可提交评价。"
    ok, reason = can_review(user, appointment)
    if not ok:
        return None, reason
    if not isinstance(rating, int) or not (MIN_RATING <= rating <= MAX_RATING):
        return None, f"评分必须为 {MIN_RATING}-{MAX_RATING} 之间的整数。"
    feedback = FeedbackRepository.create(
        user_id=user.id,
        service_id=appointment.service_id,
        appointment_id=appointment.id,
        rating=rating,
        content=(content or "").strip() or None,
    )
    return feedback, ""


def list_reviewable_appointments(user):
    """列出当前用户可评价的预约（已完成且未评价）。

    通过 AppointmentRepository 的 NOT EXISTS 查询一次取回，避免逐条预约查评价。
    """
    return AppointmentRepository.list_reviewable_by_user(user.id)
