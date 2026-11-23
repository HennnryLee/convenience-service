"""表驱动编程（Table-Driven Programming）三种查表方式。

对齐《基于案例的软件构造教程》4.5.2：
  "任何使用逻辑语句的情况都可以用存储了信息的读取表的操作" —— 把复杂的逻辑
  编织在表中而不是编织在代码里，使程序结构更简洁、逻辑更清晰、易修改扩展。

教材把表的查询方式归为三种，本模块各给一个系统内真实用途：
  1. **直接访问**：以数据本身（或其编码）为下标，一次取值    —— 分类码 → 分类名/图标；
  2. **阶梯访问**：表中存放的是数据区间，顺序扫描隐含比较      —— 价格 → 价格档位；
  3. **索引访问**：先由数据算出索引，再用索引查表            —— 耗时分钟数 → 耗时档位。

这样新增一个分类、调整一档价格，只改表、不改任何 if/elif 分支。
"""
from __future__ import annotations

from app.utils.constants import SERVICE_CATEGORIES

# ------------------------------------------------------------------ 1. 直接访问
# 以分类码直接作键（等价于教材"用字符码作数组下标"），O(1) 取值。
CATEGORY_BADGES = {
    "government": "政务",
    "life": "生活",
    "medical": "医疗",
    "education": "教育",
    "repair": "维修",
}


def category_badge(code):
    """直接访问：分类码 → 角标文案。未知分类回退为"其它"，不抛异常（防御性）。"""
    return CATEGORY_BADGES.get(code, "其它")


def category_label(code):
    """直接访问：分类码 → 分类全称。"""
    return SERVICE_CATEGORIES.get(code, "其它")


# ------------------------------------------------------------------ 2. 阶梯访问
# 表中每项是一个"上界 → 档位"的区间，按顺序比较即隐含了 if-elif 链（教材例 4.5 成绩等级）。
PRICE_LADDER = (
    (0, "免费"),
    (30, "低价"),
    (80, "中等"),
    (150, "较高"),
)


def price_level(price):
    """阶梯访问：价格 → 档位文案。

    前置条件：price 为数值且 >= 0（由调用方保证，负数按免费处理属防御性兜底）。
    """
    value = float(price or 0)
    for upper_bound, label in PRICE_LADDER:
        if value <= upper_bound:
            return label
    return "高价"


# ------------------------------------------------------------------ 3. 索引访问
# 先由耗时算出"档位索引"，再用索引取值：0=快速、1=常规、2=较慢、3=其他。
DURATION_INDEX = ("快速", "常规", "较慢", "其他")
DURATION_STEPS = (30, 60, 120)  # 分钟：<=30 归 0，<=60 归 1，<=120 归 2，其余归 3


def duration_index(minutes):
    """索引访问：由耗时计算档位下标（表的下标由数据换算得到，而非直接作为键）。"""
    value = int(minutes or 0)
    for index, step in enumerate(DURATION_STEPS):
        if value <= step:
            return index
    return len(DURATION_STEPS)


def duration_level(minutes):
    """索引访问：耗时 → 档位文案。"""
    return DURATION_INDEX[duration_index(minutes)]
