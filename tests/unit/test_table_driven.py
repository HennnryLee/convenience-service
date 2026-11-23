"""表驱动编程单元测试（教材 4.5.2）。

三种查表方式各测边界，并用"规则表对照"证明查表结果与手工 if/elif 规则完全等价：
    把知识放进表里，代码只剩一次查表，测试只需验证"表 + 查表函数"这一处。
"""
import pytest

from app.utils.table_driven import (
    CATEGORY_BADGES,
    category_badge,
    category_label,
    duration_index,
    duration_level,
    price_level,
)


# ------------------------------------------------------------------ 直接访问
@pytest.mark.parametrize(
    "code,expected",
    [
        ("government", "政务"),
        ("life", "生活"),
        ("medical", "医疗"),
        ("education", "教育"),
        ("repair", "维修"),
    ],
)
def test_category_badge_direct_access(code, expected):
    assert category_badge(code) == expected


def test_category_badge_falls_back_for_unknown_code():
    """未知分类不抛异常，回退为"其它"（防御性编程：外部数据可能不可信）。"""
    assert category_badge("not-exist") == "其它"
    assert category_badge(None) == "其它"


def test_category_label_matches_constant_table():
    for code, text in {"government": "政务服务", "life": "生活服务"}.items():
        assert category_label(code) == text


# ------------------------------------------------------------------ 阶梯访问
@pytest.mark.parametrize(
    "price,expected",
    [
        (0, "免费"),        # 下边界
        (1, "低价"),
        (30, "低价"),       # 档位边界（含）
        (30.01, "中等"),    # 刚刚越过边界
        (50, "中等"),
        (80, "中等"),       # 档位边界（含）
        (150, "较高"),      # 档位边界（含）
        (150.5, "高价"),    # 最后一档
        (9999, "高价"),
    ],
)
def test_price_level_ladder(price, expected):
    assert price_level(price) == expected


def test_price_level_matches_reference_rule():
    """与朴素 if/elif 规则逐点比对：证明表驱动实现与规则定义等价。"""

    def reference(p):
        if p <= 0:
            return "免费"
        if p <= 30:
            return "低价"
        if p <= 80:
            return "中等"
        if p <= 150:
            return "较高"
        return "高价"

    for price in [0, 5, 29.9, 30, 30.1, 79, 80, 80.1, 149, 150, 150.1, 1000]:
        assert price_level(price) == reference(price)


# ------------------------------------------------------------------ 索引访问
@pytest.mark.parametrize(
    "minutes,index",
    [(0, 0), (30, 0), (31, 1), (60, 1), (61, 2), (120, 2), (121, 3), (1000, 3)],
)
def test_duration_index(minutes, index):
    assert duration_index(minutes) == index


@pytest.mark.parametrize(
    "minutes,expected",
    [(30, "快速"), (60, "常规"), (120, "较慢"), (180, "其他"), (0, "快速")],
)
def test_duration_level(minutes, expected):
    assert duration_level(minutes) == expected


def test_tables_are_read_only_by_convention():
    """表是"应用知识"的唯一来源：分类角标不应出现表外键（新增分类须同步改表）。"""
    assert set(CATEGORY_BADGES).issubset({"government", "life", "medical", "education", "repair"})


def test_service_detail_exposes_table_driven_fields(app, service):
    """服务详情把阶梯/索引查表结果直接交给模板，模板中不再写分支判断。"""
    from app.services.service_catalog import get_service_detail

    detail = get_service_detail(service.id)
    assert detail["price_level"] == "低价"      # 20 元落在 (0,30]
    assert detail["duration_level"] == "快速"   # 30 分钟落在 <=30
    assert detail["category_badge"] == "政务"
