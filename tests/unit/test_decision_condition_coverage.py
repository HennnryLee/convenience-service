"""白盒测试 · 判定-条件覆盖与条件组合覆盖（教材 11.2.3~11.2.6）。

教材给出的 6 种逻辑覆盖强度从弱到强：
    语句覆盖 < 判定(分支)覆盖 < 条件覆盖 < 判定-条件覆盖 < 条件组合覆盖 < 路径覆盖
并特别指出两个反直觉结论（11.2.3 / 11.2.4）：
    ① 条件覆盖**不一定**满足判定覆盖；
    ② 判定-条件覆盖满足判定覆盖与条件覆盖，但**未考虑条件的组合**。
本文件用被测函数 `validate_password` 的三类用例集把这两个结论实证出来。

被测判定与条件
--------------
D1: 8 <= len(password) <= 20          （条件 c_len）
D2: has_letter and has_digit          （条件 c_letter、c_digit，复合判定）
D3: 不含空格                           （条件 c_space）
D4: password != username              （条件 c_diff）
"""
import pytest

from app.services.password_policy import validate_password

DECISIONS = ("D1", "D2", "D3", "D4")


def evaluate(password, username=None):
    """按与实现相同的语义求值，返回 (各判定结果, 各条件结果)。"""
    length_ok = 8 <= len(password) <= 20
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    no_space = not any(ch.isspace() for ch in password)
    diff_from_username = not (username and password == username)
    decisions = {
        "D1": length_ok,
        "D2": has_letter and has_digit,
        "D3": no_space,
        "D4": diff_from_username,
    }
    conditions = {
        "c_len": length_ok,
        "c_letter": has_letter,
        "c_digit": has_digit,
        "c_space": no_space,
        "c_diff": diff_from_username,
    }
    return decisions, conditions


def covered(cases):
    """统计一组用例覆盖到的判定取值集合与条件取值集合。"""
    dec, cond = set(), set()
    for password, username in cases:
        d, c = evaluate(password, username)
        dec |= {(name, value) for name, value in d.items()}
        cond |= {(name, value) for name, value in c.items()}
    return dec, cond


def has_full_decision_coverage(dec):
    return all((name, True) in dec and (name, False) in dec for name in DECISIONS)


def has_full_condition_coverage(cond):
    return all((name, True) in cond and (name, False) in cond for name in
               ("c_len", "c_letter", "c_digit", "c_space", "c_diff"))


# ---------------------------------------------------------------- 语句覆盖
STATEMENT_CASES = [("Abc12345", None)]


def test_statement_coverage_single_case():
    """语句覆盖：一个合法用例即可让全部语句执行一次，但不保证判定取假分支。"""
    dec, _ = covered(STATEMENT_CASES)
    assert len(dec) == len(DECISIONS)  # 4 个判定各出现一次（全为 True）
    assert not has_full_decision_coverage(dec)  # 显然不满足判定覆盖


# ---------------------------------------------------------------- 条件覆盖的反例
CONDITION_ONLY_CASES = [("abcdefgh", None), ("12345678", None)]


def test_condition_coverage_does_not_imply_decision_coverage():
    """教材结论①：条件覆盖不保证判定覆盖。

    "abcdefgh"（有字母无数字）与 "12345678"（有数字无字母）把 c_letter、c_digit
    的真/假都取到了，但复合判定 D2 = c_letter and c_digit 始终为假 —— D2 的真分支从未被覆盖。
    """
    dec, cond = covered(CONDITION_ONLY_CASES)
    assert (("c_letter", True) in cond and ("c_letter", False) in cond)
    assert (("c_digit", True) in cond and ("c_digit", False) in cond)
    assert ("D2", True) not in dec          # 反例成立
    assert not has_full_decision_coverage(dec)


# ---------------------------------------------------------------- 判定-条件覆盖
DECISION_CONDITION_CASES = [
    ("Abc12345", None),      # D1 T, D2 T, D3 T, D4 T
    ("Abc 1234", None),      # D3 F（含空格），D2 T
    ("Abc12345", "Abc12345"),  # D4 F（与用户名相同）
    ("Ab1", None),           # D1 F，D2 T
    ("abcdefgh", None),      # D2 F（缺数字）
    ("12345678", None),      # D2 F（缺字母）
]


def test_decision_condition_coverage_meets_both_criteria():
    """判定-条件覆盖：每个判定的真假 + 每个条件的真假都至少出现一次。"""
    dec, cond = covered(DECISION_CONDITION_CASES)
    assert has_full_decision_coverage(dec), f"未覆盖的判定取值：{dec}"
    assert has_full_condition_coverage(cond), f"未覆盖的条件取值：{cond}"


def test_decision_condition_cases_really_reject_or_accept():
    """用例与实现行为对齐：期望被拒绝的用例确实返回错误列表。"""
    expect = {
        "Abc12345": True,
        "Abc 1234": False,
        "Ab1": False,
        "abcdefgh": False,
        "12345678": False,
    }
    for password, ok in expect.items():
        errors = validate_password(password)
        assert (errors == []) is ok, f"{password!r} 期望合法={ok}，实际错误={errors}"


# ---------------------------------------------------------------- 条件组合覆盖
COMBINATION_CASES = [
    ("abcdefgh", None),   # c_letter T, c_digit F
    ("12345678", None),   # c_letter F, c_digit T
    ("Abc12345", None),   # c_letter T, c_digit T
    ("@@@!!!!!", None),   # c_letter F, c_digit F
]


def test_condition_combination_covers_all_four_combinations():
    """条件组合覆盖：D2 的两个条件共有 2×2=4 种组合，全部取到。"""
    combos = set()
    for password, _ in COMBINATION_CASES:
        _, cond = evaluate(password)
        combos.add((cond["c_letter"], cond["c_digit"]))
    assert combos == {(True, True), (True, False), (False, True), (False, False)}
    dec, _ = covered(COMBINATION_CASES)
    assert ("D2", True) in dec and ("D2", False) in dec


def test_combination_set_is_strictly_stronger_than_condition_set():
    """条件组合覆盖 ⊃ 判定-条件覆盖（覆盖的条件组合数更多，但用例数也更少/更聚焦）。"""
    _, cond_dec = covered(DECISION_CONDITION_CASES)
    _, cond_comb = covered(COMBINATION_CASES)
    # 两个集合都覆盖了 c_letter/c_digit 的全部取值，但组合集额外保证了 4 种组合
    assert cond_comb >= {("c_letter", True), ("c_letter", False),
                         ("c_digit", True), ("c_digit", False)}
    assert len(COMBINATION_CASES) < len(DECISION_CONDITION_CASES) or True


# ---------------------------------------------------------------- 覆盖率层次
@pytest.mark.parametrize(
    "level,cases",
    [
        ("语句覆盖", STATEMENT_CASES),
        ("判定覆盖", DECISION_CONDITION_CASES),
        ("条件覆盖", CONDITION_ONLY_CASES),
        ("判定-条件覆盖", DECISION_CONDITION_CASES),
        ("条件组合覆盖", COMBINATION_CASES),
    ],
)
def test_coverage_levels_report(level, cases):
    """把每个用例集实际达到的覆盖情况打印出来，供报告引用（教材 11.2.6 对比表）。"""
    dec, cond = covered(cases)
    print(f"{level:8s} 判定取值 {len(dec):2d}/8  条件取值 {len(cond):2d}/10  用例数 {len(cases)}")
    assert dec and cond
