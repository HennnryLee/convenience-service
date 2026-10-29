"""在线预约服务：编排"数据查询 → 规则校验 → 落库"的完整流程。

设计：规则判定全部委托给 appointment_rules（纯函数），
本模块只负责取数、拼装上下文、调用规则、写库 —— 职责单一，便于测试。
"""
from datetime import date

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.service_repository import ServiceRepository
from app.services.appointment_rules import (
    AppointmentContext,
    can_cancel,
    can_transition,
    remaining_capacity,
    validate_new_appointment,
)
from app.utils.constants import APPOINTMENT_TRANSITIONS, TIME_SLOTS
from app.utils.validators import is_valid_phone


def build_context(service, appointment_date, time_slot, user_id=None):
    """根据数据库当前状态拼装预约上下文（供规则层使用）。"""
    used = AppointmentRepository.count_active(service.id, appointment_date, time_slot)
    duplicate = (
        AppointmentRepository.has_active_duplicate(user_id, service.id, appointment_date, time_slot)
        if user_id
        else False
    )
    return AppointmentContext(
        service_online=service.is_online,
        capacity=service.daily_capacity,
        used=used,
        has_duplicate=duplicate,
    )


def validate_basic_fields(contact_name, contact_phone):
    """表单基本信息校验（与规则层解耦的纯校验）。"""
    errors = {}
    if not contact_name or len(contact_name.strip()) < 2:
        errors["contact_name"] = "请填写真实姓名（至少 2 个字符）。"
    if not is_valid_phone(contact_phone):
        errors["contact_phone"] = "请填写 11 位有效手机号。"
    return errors


def create_appointment(user, service_id, appointment_date, time_slot, contact_name, contact_phone,
                       remark=None):
    """提交预约。

    后置条件：成功返回 (appointment, [])；失败返回 (None, 错误信息列表)。
    不变量：任何失败路径都不写库（先校验后提交）。
    """
    # 1) 表单字段校验（便宜的校验先做）
    form_errors = validate_basic_fields(contact_name, contact_phone)
    if form_errors:
        return None, list(form_errors.values())

    # 2) 服务存在性校验
    service = ServiceRepository.get(service_id)
    if service is None:
        return None, ["所选服务不存在或已下架。"]

    # 3) 业务规则校验（需要查询数据库，故放在最后）
    rule_errors = validate_new_appointment(
        build_context(service, appointment_date, time_slot, user.id),
        appointment_date,
        time_slot,
    )
    if rule_errors:
        return None, rule_errors

    appointment = AppointmentRepository.create(
        user_id=user.id,
        service_id=service.id,
        appointment_date=appointment_date,
        time_slot=time_slot,
        contact_name=contact_name.strip(),
        contact_phone=contact_phone.strip(),
        remark=(remark or "").strip() or None,
        status="pending",
    )
    return appointment, []


def cancel_appointment(appointment, operator, is_admin=False):
    """取消预约。

    前置条件：appointment 存在；operator 为当前登录用户。
    权限：本人可取消自己的预约，管理员可取消任意预约。
    """
    if appointment is None:
        return False, "预约记录不存在。"
    if not is_admin and appointment.user_id != operator.id:
        return False, "只能取消本人的预约。"
    if not can_cancel(appointment.status):
        return False, f"当前状态（{appointment.status_text}）不可取消。"
    appointment.change_status("cancelled")
    AppointmentRepository.save(appointment)
    return True, "预约已取消。"


def change_status(appointment, new_status):
    """管理员推进预约状态（受表驱动状态机约束）。"""
    if appointment is None:
        return False, "预约记录不存在。"
    if not can_transition(appointment.status, new_status):
        allowed = "、".join(sorted(APPOINTMENT_TRANSITIONS.get(appointment.status, set()))) or "无"
        return False, f"不允许从「{appointment.status_text}」变更为「{new_status}」，可选：{allowed}。"
    appointment.change_status(new_status)
    AppointmentRepository.save(appointment)
    return True, f"预约状态已更新为「{appointment.status_text}」。"


def get_slot_availability(service, appointment_date=None):
    """返回某服务指定日期各时段的剩余名额（用于详情页展示）。

    返回：[{slot, remaining, capacity, full}, ...]
    """
    appointment_date = appointment_date or date.today()
    result = []
    for slot in TIME_SLOTS:
        used = AppointmentRepository.count_active(service.id, appointment_date, slot)
        remaining = remaining_capacity(service.daily_capacity, used)
        result.append(
            {
                "slot": slot,
                "remaining": remaining,
                "capacity": service.daily_capacity,
                "full": remaining <= 0,
            }
        )
    return result
