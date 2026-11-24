"""性质测试（随机化 + 不变量），不使用额外依赖，固定种子保证可复现。

与示例测试的区别：示例测试挑几个代表值，性质测试在较大输入空间上验证
"无论输入是什么，某条不变量都必须成立"。这里覆盖四个核心纯函数：
  - remaining_capacity  ：结果始终落在 [0, capacity]，且等于 max(capacity-used, 0)；
  - is_slot_started/ended：与"日期 + 分钟数"参考实现逐点一致；
  - price_level         ：与朴素 if/elif 参考规则逐点一致（表驱动等价性）；
  - parse_page          ：任意输入都返回 >=1 的整数。
"""
import random
from datetime import date, datetime, timedelta

from app.services.appointment_rules import (
    is_slot_ended,
    is_slot_started,
    remaining_capacity,
)
from app.utils.constants import TIME_SLOTS
from app.utils.pagination import parse_page
from app.utils.table_driven import price_level

SEED = 20261124
RANDOM = random.Random(SEED)


def test_remaining_capacity_property():
    for _ in range(500):
        capacity = RANDOM.randint(0, 100)
        used = RANDOM.randint(0, 200)
        result = remaining_capacity(capacity, used)
        assert 0 <= result <= capacity
        assert result == max(capacity - used, 0)


def test_slot_started_and_ended_match_reference_implementation():
    today = date.today()
    for _ in range(500):
        target = today + timedelta(days=RANDOM.randint(-3, 3))
        slot = RANDOM.choice(TIME_SLOTS)
        start_text, end_text = slot.split("-")
        start = int(start_text[:2]) * 60 + int(start_text[3:])
        end = int(end_text[:2]) * 60 + int(end_text[3:])
        now = datetime(target.year, target.month, target.day, RANDOM.randint(0, 23), RANDOM.randint(0, 59))
        minute = now.hour * 60 + now.minute

        expected_started = target == now.date() and minute >= start
        expected_ended = target < now.date() or (target == now.date() and minute >= end)
        assert is_slot_started(target, slot, now) is expected_started
        assert is_slot_ended(target, slot, now) is expected_ended


def _reference_price_level(price):
    value = float(price or 0)
    if value <= 0:
        return "免费"
    if value <= 30:
        return "低价"
    if value <= 80:
        return "中等"
    if value <= 150:
        return "较高"
    return "高价"


def test_price_level_matches_reference_over_random_prices():
    for _ in range(500):
        price = round(RANDOM.uniform(0, 500), 2)
        assert price_level(price) == _reference_price_level(price)


def test_parse_page_always_returns_positive_integer():
    samples = [None, "", "abc", "0", "-1", "1", "42", "3.14", 0, -10, 7, 1.9]
    samples += ["".join(RANDOM.choices("0123456789abc.- ", k=RANDOM.randint(0, 8))) for _ in range(200)]
    for value in samples:
        page = parse_page(value)
        assert isinstance(page, int) and page >= 1


def test_time_slots_are_disjoint_and_ordered():
    """时段表本身的性质：按时间升序、互不重叠，便于"剩余时段"展示。"""
    from app.utils.time_slots import parse_slot

    bounds = [parse_slot(slot) for slot in TIME_SLOTS]
    assert all(bound is not None for bound in bounds)
    for previous, current in zip(bounds, bounds[1:], strict=False):
        assert previous[1] <= current[0]
