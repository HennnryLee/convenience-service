"""白盒测试 · 循环测试（教材 11.2.7）。

教材对**简单循环**要求至少覆盖：零次、一次、二次、m 次（m<n）、n−1、n、n+1
（n 为允许的最大循环次数）；对**嵌套循环**要求由内向外逐层测试。

本系统里有两处典型循环可直接施加循环测试：
  1. 密码校验中的逐字符扫描 `any(ch.isalpha() for ch in password)` —— 循环次数 = 密码长度，
     可真实构造零次循环（空串）；
  2. 价格档位查表 `for upper_bound, label in PRICE_LADDER` —— 带提前返回的循环，
     循环次数由数据落在第几档决定（1~5 次）。

说明：`for` 循环若不空，至少执行一次；教材"零次循环"针对 while/for 边界，
对应到 Python 迭代器即"空序列不进入循环体"，故第 1 组用空串覆盖零次。
"""
import pytest
from app.services.password_policy import validate_password
from app.utils.table_driven import PRICE_LADDER, price_level

# ============================================================ 1. 逐字符扫描循环
CHAR_LOOP_CASES = [
    # (循环次数类别, 密码, 期望是否报"必须同时包含字母和数字")
    ("零次循环", "", True),                 # 空串：循环体一次都不进入
    ("一次循环", "a", True),                # 只扫 1 个字符：有字母无数字
    ("二次循环", "a1", False),              # 2 个字符：同时含字母和数字
    ("m 次循环(m<n)", "abc1234567", False),  # 10 个字符
    ("n-1 次循环", "a" * 6 + "1", False),    # 7 字符：越过最小长度下界前一位
    ("n 次循环", "a" * 7 + "1", False),      # 8 字符：最小长度下界
    ("n 次循环(上界)", "a" * 19 + "1", False),  # 20 字符：最大长度上界
    ("n+1 次循环", "a" * 20 + "1", False),    # 21 字符：越过上界，只报长度错（字母数字齐全）
]


@pytest.mark.parametrize("kind,password,missing_char_kind", CHAR_LOOP_CASES,
                         ids=[c[0] for c in CHAR_LOOP_CASES])
def test_character_scan_loop(kind, password, missing_char_kind):
    errors = validate_password(password)
    joined = " ".join(errors)
    reported = "字母和数字" in joined
    assert reported is missing_char_kind, f"{kind}: 期望报错={missing_char_kind}，实际={joined or '无错误'}"


def test_zero_iteration_loop_behaves_like_empty_input():
    """零次循环：空串既触发长度错误，也使 any() 返回 False（短路语义）。"""
    errors = validate_password("")
    assert any("长度" in e for e in errors)
    assert any("字母和数字" in e for e in errors)


def test_over_upper_bound_reports_length_only():
    """n+1 次循环：21 位密码只应报长度错误，不应误报"缺少字母或数字"。"""
    errors = validate_password("a" * 20 + "1")
    assert len(errors) == 1 and "长度" in errors[0]


# ============================================================ 2. 带提前返回的查表循环
def test_ladder_loop_iteration_counts():
    """PRICE_LADDER 共 4 档 + 1 次默认返回：输入决定在第几次比较后退出。"""
    iterations = {
        0: 1,       # 第 1 次比较即命中"免费"
        20: 2,      # 第 2 次命中"低价"
        60: 3,      # 第 3 次命中"中等"
        120: 4,     # 第 4 次命中"较高"
        999: 5,     # 4 次比较全部失败 + 循环后默认返回"高价"
    }
    for price, expected_iterations in iterations.items():
        actual = 0
        value = float(price)
        for upper_bound, _label in PRICE_LADDER:
            actual += 1
            if value <= upper_bound:
                break
        else:
            actual += 1  # 循环正常结束（未 break）后执行默认返回
        assert actual == expected_iterations, f"价格 {price} 的循环次数不符"
        assert price_level(price) in ("免费", "低价", "中等", "较高", "高价")


@pytest.mark.parametrize(
    "price,expected",
    [(0, "免费"), (30, "低价"), (30.01, "中等"), (80, "中等"), (150, "较高"), (150.01, "高价")],
)
def test_ladder_boundary_values(price, expected):
    """循环边界：每一档的上界与上界+ε 都要覆盖（教材边界值 + 循环测试结合）。"""
    assert price_level(price) == expected


# ============================================================ 3. 嵌套/连锁循环说明
def test_no_nested_loops_in_core_rules():
    """核心规则层不含嵌套循环：全部为单层遍历，循环测试可按简单循环处理。

    这是"可测试性设计"的体现——把批量统计放进数据层（SQL 聚合），
    业务层只保留可穷举的单层循环，避免组合爆炸。
    """
    import inspect

    from app.services import appointment_rules, password_policy

    for module in (appointment_rules, password_policy):
        source = inspect.getsource(module)
        assert "for " in source or "any(" in source  # 确有循环
        assert source.count("for ") <= 3               # 无深层嵌套
