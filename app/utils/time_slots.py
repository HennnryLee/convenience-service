"""时段解析（预约时间的单一事实来源）。

背景：原先 ``is_slot_started`` 与 ``is_slot_ended`` 各自写了一遍
``slot.split("-")[0].split(":")`` 的解析逻辑；新增「当天已结束」「剩余时段」
等规则时，很容易只改一处，造成两套时间语义。本模块把"字符串 → 分钟数"的
解析与合法性判断收敛为一个纯函数，规则层只做比较。

教材对应：《软件构造》6.1 代码重构中的「提炼函数 / 消除重复代码」，
以及 2.3 模块化中的「功能内聚」——一个函数只回答一个问题。
"""
from __future__ import annotations

import re

from app.utils.constants import TIME_SLOTS

MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
_SLOT_PATTERN = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")


def parse_slot(slot: str | None) -> tuple[int, int] | None:
    """把 ``"09:00-10:00"`` 解析为 ``(开始分钟, 结束分钟)``。

    前置条件：slot 为任意对象（非字符串返回 None，不抛异常）。
    后置条件：格式合法且开始 < 结束时返回二元组，否则返回 None。
    不变量：不修改入参，不依赖系统时间。
    """
    if not isinstance(slot, str):
        return None
    matched = _SLOT_PATTERN.match(slot)
    if matched is None:
        return None
    start_hour, start_minute, end_hour, end_minute = (int(part) for part in matched.groups())
    if not all(0 <= hour < HOURS_PER_DAY for hour in (start_hour, end_hour)):
        return None
    if not all(0 <= minute < MINUTES_PER_HOUR for minute in (start_minute, end_minute)):
        return None
    start = start_hour * MINUTES_PER_HOUR + start_minute
    end = end_hour * MINUTES_PER_HOUR + end_minute
    if start >= end:
        return None
    return start, end


def is_known_slot(slot: str | None) -> bool:
    """是否属于系统开放时段表（TIME_SLOTS）。"""
    return isinstance(slot, str) and slot in TIME_SLOTS


def now_minutes(now) -> int:
    """把 datetime 折算为"当天第几分钟"，便于与时段边界直接比较。"""
    return now.hour * MINUTES_PER_HOUR + now.minute


def slot_start(slot: str) -> int | None:
    """时段开始分钟；非法时段返回 None。"""
    bounds = parse_slot(slot)
    return bounds[0] if bounds else None


def slot_end(slot: str) -> int | None:
    """时段结束分钟；非法时段返回 None。"""
    bounds = parse_slot(slot)
    return bounds[1] if bounds else None
