"""预约管理模块 —— 业务规则层（纯函数，不依赖数据库与 Web 框架）。

设计要点：
  1. **纯逻辑**：所有外部数据查询结果通过 AppointmentContext 传入，
     因此本模块可脱离数据库/Web 完成单元测试（可测试性 = 低耦合的体现）。
  2. **表驱动**：状态流转查 APPOINTMENT_TRANSITIONS 表，新增状态只改常量不改代码。
  3. **契约式编程**：每个函数用 require/ensure/invariant 显式声明前置条件、后置条件
     与不变式（教材 4.9.3"期望什么、保证什么、保持什么"），见 docs/12。
"""
from dataclasses import dataclass
from datetime import date

from app.utils.constants import APPOINTMENT_TRANSITIONS, TIME_SLOTS
from app.utils.contracts import ensure, invariant, require

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
    """前置条件：slot 为字符串或 None；后置条件：返回 slot 是否在开放时段表中。"""
    require(slot is None or isinstance(slot, str), "slot 必须是字符串或 None")
    result = isinstance(slot, str) and slot in TIME_SLOTS
    ensure(isinstance(result, bool), "is_valid_slot 必须返回布尔值")
    return result


def remaining_capacity(capacity, used):
    """剩余名额。

    前置条件：capacity、used 均为非负整数（超卖时 used 可大于 capacity）。
    后置条件：0 <= 返回值 <= capacity。
    不变量：函数不修改入参，TIME_SLOTS 表保持只读不变。
    """
    require(isinstance(capacity, int) and isinstance(used, int), "capacity/used 必须是整数")
    require(capacity >= 0 and used >= 0, "capacity/used 不能为负数")
    slots_snapshot = tuple(TIME_SLOTS)

    remain = max(capacity - used, 0)

    ensure(isinstance(remain, int) and 0 <= remain <= capacity, "剩余名额必须落在 [0, capacity] 内")
    invariant(tuple(TIME_SLOTS) == slots_snapshot, "时段表在计算过程中不得被修改")
    return remain


def next_statuses(status):
    """返回某状态可直接迁移到的状态列表（表驱动）。"""
    require(isinstance(status, str), "status 必须是字符串")
    return sorted(APPOINTMENT_TRANSITIONS.get(status, set()))


def can_transition(current, new):
    """判定状态流转是否合法。未知状态一律返回 False（安全默认）。"""
    require(isinstance(current, str) and isinstance(new, str), "状态码必须是字符串")
    return new in APPOINTMENT_TRANSITIONS.get(current, set())


def can_cancel(status):
    """用户能否主动取消：等价于"可迁移到 cancelled"。"""
    return can_transition(status, "cancelled")


# ------------------------------------------------------------------ 预约校验
def validate_new_appointment(context, appointment_date, slot, today=None, max_days_ahead=MAX_DAYS_AHEAD):
    """校验一次新预约是否可提交。

    前置条件：
        - context 为 AppointmentContext；
        - appointment_date 为 datetime.date 或 None（None 表示用户未选择）；
        - today 为"今天"的日期（默认取系统日期），便于测试注入固定时间；
        - max_days_ahead 为正整数。
    后置条件：
        - 返回错误信息列表；列表为空表示校验通过；每条错误都是非空字符串。
    不变量：
        - 无论输入如何，函数不修改入参，也不改动时段表。
    """
    require(isinstance(context, AppointmentContext), "context 必须是 AppointmentContext")
    require(appointment_date is None or isinstance(appointment_date, date), "appointment_date 必须是 date 或 None")
    require(isinstance(max_days_ahead, int) and max_days_ahead >= 1, "max_days_ahead 必须是正整数")
    slots_snapshot = tuple(TIME_SLOTS)

    errors = []
    if today is None:
        today = date.today()
    require(isinstance(today, date), "today 必须是 date")

    if not context.service_online:
        errors.append("该服务已下架，暂不可预约。")

    if appointment_date is None:
        errors.append("请选择预约日期。")
        ensure(isinstance(errors, list) and all(isinstance(e, str) and e for e in errors), "错误列表元素必须非空")
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

    ensure(isinstance(errors, list) and all(isinstance(e, str) and e for e in errors), "错误列表元素必须非空")
    invariant(tuple(TIME_SLOTS) == slots_snapshot, "时段表在校验过程中不得被修改")
    return errors
