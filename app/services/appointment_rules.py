"""预约管理模块 —— 业务规则层（纯函数，不依赖数据库与 Web 框架）。

设计要点：
  1. **纯逻辑**：所有外部数据查询结果通过 AppointmentContext 传入，
     因此本模块可脱离数据库/Web 完成单元测试（可测试性 = 低耦合的体现）。
  2. **表驱动**：状态流转查 APPOINTMENT_TRANSITIONS 表，新增状态只改常量不改代码。
  3. **契约式设计**：每个函数明确前置条件、后置条件与不变量（见 docs/06）。
"""
from dataclasses import dataclass
from datetime import date

from app.utils.constants import APPOINTMENT_TRANSITIONS, TIME_SLOTS

MAX_DAYS_AHEAD = 30  # 最多可预约未来 30 天


@dataclass(frozen=True)
class AppointmentContext:
    """预约所需的外部事实（由数据层查询后传入）。

    - service_online：服务是否处于上架状态
    - capacity      ：该时段总容量
    - used          ：该时段已被占用的数量
    - has_duplicate ：同一用户是否已预约过同一时段
    """

    service_online: bool
    capacity: int
    used: int
    has_duplicate: bool = False


# ------------------------------------------------------------------ 基础判定
def is_valid_slot(slot):
    """前置条件：slot 为字符串；后置条件：返回 slot 是否在开放时段表中。"""
    return slot in TIME_SLOTS


def remaining_capacity(capacity, used):
    """不变量：返回值恒 >= 0（即使数据异常导致超卖，也不返回负数）。"""
    return max(capacity - used, 0)


def next_statuses(status):
    """返回某状态可直接迁移到的状态列表（表驱动）。"""
    return sorted(APPOINTMENT_TRANSITIONS.get(status, set()))


def can_transition(current, new):
    """判定状态流转是否合法。未知状态一律返回 False（安全默认）。"""
    return new in APPOINTMENT_TRANSITIONS.get(current, set())


def can_cancel(status):
    """用户能否主动取消：等价于"可迁移到 cancelled"。"""
    return can_transition(status, "cancelled")


# ------------------------------------------------------------------ 预约校验
def validate_new_appointment(context, appointment_date, slot, today=None, max_days_ahead=MAX_DAYS_AHEAD):
    """校验一次新预约是否可提交。

    前置条件：
        - context 为 AppointmentContext；
        - appointment_date 为 datetime.date；
        - today 为"今天"的日期（默认取系统日期），便于测试注入固定时间；
        - max_days_ahead 为正整数。
    后置条件：
        - 返回错误信息列表；列表为空表示校验通过。
    不变量：
        - 无论输入如何，函数不抛异常、不修改入参。
    """
    errors = []
    if today is None:
        today = date.today()

    if not context.service_online:
        errors.append("该服务已下架，暂不可预约。")

    if appointment_date is None:
        errors.append("请选择预约日期。")
        return errors

    if appointment_date < today:
        errors.append("不能预约过去的日期。")
    elif (appointment_date - today).days > max_days_ahead:
        errors.append(f"仅可预约未来 {max_days_ahead} 天内的服务。")

    if not is_valid_slot(slot):
        errors.append(f"预约时段无效，可选时段：{'、'.join(TIME_SLOTS)}。")

    if context.has_duplicate:
        errors.append("你已预约该时段，请勿重复提交。")

    if remaining_capacity(context.capacity, context.used) <= 0:
        errors.append("该时段预约名额已满，请选择其它时段。")

    return errors
