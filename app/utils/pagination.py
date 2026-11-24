"""分页参数与枚举过滤参数解析（表现层共用的小工具）。

为什么单独成模块：
  - `request.args.get("page", 1, type=int)` 遇到 ``page=0``、``page=abc`` 时行为不一致，
    前者可能让 SQLAlchemy 抛错或返回空页，后者静默回退；不同视图各写一遍容易漂移；
  - 状态筛选必须走白名单，否则任意字符串会进入查询（虽然参数化查询不会注入，
    但会得到"筛选了却查不到"的困惑结果）。
"""
from __future__ import annotations

from collections.abc import Iterable


def parse_page(value, default: int = 1) -> int:
    """把查询参数转成 >=1 的页码；非法值回退到 default。"""
    try:
        page = int(value)
    except (TypeError, ValueError):
        return default
    return max(page, 1)


def parse_choice(value, allowed: Iterable[str], default=None):
    """枚举白名单过滤：值不在 allowed 中时返回 default。"""
    allowed_set = set(allowed)
    return value if value in allowed_set else default
