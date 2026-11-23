"""变异测试（教材 11.5）：用一组"人工注入缺陷"的变异体检验测试集的有效性。

原理（教材 11.5）：
    若测试集 T 能发现不了某个变异体 M(P) 的错误，说明 T 要么没覆盖到那段逻辑，
    要么断言太弱。T 杀死的变异体比例即**变异分数（Mutation Score）**：
        变异分数 = 被杀死变异体数 / (有效变异体总数)
    未被杀死的变异体有三种可能：① 与源程序功能等价；② 测试数据不足；③ 源程序本身有错。

实现：逐个把单点变异写入源文件 → 运行对应单元测试 → 测试失败即"杀死" → 恢复原文件
（用 try/finally + 校验和保证源文件一定被还原）。

用法： python scripts/mutation_test.py
输出： reports/mutation_report.md
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PY = sys.executable

RULES = os.path.join(BASE, "app", "services", "appointment_rules.py")
POLICY = os.path.join(BASE, "app", "services", "password_policy.py")

# (编号, 文件, 原片段, 变异片段, 变异算子, 说明)
MUTANTS = [
    ("M01", RULES, "if appointment_date < today:", "if appointment_date <= today:",
     "关系运算符变异", "把「过去日期」边界 < 改为 <=（当天也被判为过去）"),
    ("M02", RULES, ".days > max_days_ahead:", ".days >= max_days_ahead:",
     "关系运算符变异", "把「超过 30 天」改为「满 30 天即拒绝」（边界偏移）"),
    ("M03", RULES, "if remaining_capacity(context.capacity, context.used) <= 0:",
     "if remaining_capacity(context.capacity, context.used) < 0:",
     "关系运算符变异", "剩余 0 时不再判定为满员（差一错误）"),
    ("M04", RULES, "if not context.service_online:", "if context.service_online:",
     "逻辑非变异", "下架判定取反：上架服务被拒、下架服务被放行"),
    ("M05", RULES, "if context.has_duplicate:", "if not context.has_duplicate:",
     "逻辑非变异", "重复预约判定取反"),
    ("M06", RULES, "if not is_valid_slot(slot):", "if False:",
     "条件删除变异", "删除时段合法性校验（任意时段都能预约）"),
    ("M07", POLICY, "MIN_LENGTH <= len(password) <= MAX_LENGTH",
     "MIN_LENGTH < len(password) < MAX_LENGTH", "关系运算符变异", "长度边界改为开区间（8 位与 20 位被误拒）"),
    ("M08", POLICY, "if not (has_letter and has_digit):", "if not (has_letter or has_digit):",
     "逻辑运算符变异", "and 改 or：只有纯符号密码才会被拒"),
    ("M09", POLICY, "if any(ch.isspace() for ch in password):", "if False:",
     "条件删除变异", "删除空格校验"),
    ("M10", POLICY, "if username and password == username:", "if username and password != username:",
     "关系运算符变异", "与用户名相同的判定取反"),
    ("M11", RULES, 'errors.append("该时段预约名额已满，请选择其它时段。")',
     'errors.append("该时段预约名额已满。")', "消息变异", "修改提示文案（测试是否断言了完整语义）"),
    ("M12", RULES, "remain = max(capacity - used, 0)", "remain = capacity - used",
     "边界保护删除变异", "删除 max(...,0)：超卖时返回负数（破坏后置条件）"),
]

TEST_TARGETS = [
    os.path.join("tests", "unit", "test_appointment_rules.py"),
    os.path.join("tests", "unit", "test_password_policy.py"),
]


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run_tests():
    """运行相关单元测试，返回 (是否通过, 输出摘要)。"""
    proc = subprocess.run(
        [PY, "-m", "pytest", "-x", "-q", "--no-header", *TEST_TARGETS],
        cwd=BASE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    passed = proc.returncode == 0
    tail = (proc.stdout or "").strip().splitlines()
    summary = tail[-1] if tail else (proc.stderr or "")[-200:]
    return passed, summary


def main():
    # 基线：原程序必须通过，否则后续结果无意义
    ok, summary = run_tests()
    if not ok:
        raise SystemExit(f"基线测试未通过，终止变异测试：{summary}")
    print(f"[基线] 通过：{summary}")

    results = []
    for mid, path, old, new, operator, desc in MUTANTS:
        original_bytes = open(path, "rb").read()
        original = original_bytes.decode("utf-8")
        if old not in original:
            results.append((mid, operator, desc, "无效变异（片段未找到）", ""))
            print(f"[{mid}] 片段未找到，跳过")
            continue

        before = sha256(path)
        mutated = original.replace(old, new, 1)
        try:
            with open(path, "wb") as f:
                f.write(mutated.encode("utf-8"))
            # 语法无效的变异体直接记为无效
            compile(mutated, path, "exec")
            passed, summary = run_tests()
            status = "存活" if passed else "杀死"
            results.append((mid, operator, desc, status, summary))
            print(f"[{mid}] {status}（{operator}）")
        except SyntaxError:
            results.append((mid, operator, desc, "无效变异（语法错误）", ""))
            print(f"[{mid}] 语法错误，跳过")
        finally:
            # 以字节写回，保证换行符不被文本模式转换（否则哈希必然不相等）
            with open(path, "wb") as f:
                f.write(original_bytes)
            assert sha256(path) == before, f"{path} 未能恢复原状！"

    valid = [r for r in results if not r[3].startswith("无效")]
    killed = [r for r in valid if r[3] == "杀死"]
    survived = [r for r in valid if r[3] == "存活"]
    score = len(killed) / len(valid) * 100 if valid else 0

    out_dir = os.path.join(BASE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "mutation_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 变异测试报告（教材 11.5）\n\n")
        f.write(f"- 变异算子：关系运算符 / 逻辑运算符 / 逻辑非 / 条件删除 / 边界保护删除 / 消息变异\n")
        f.write(f"- 有效变异体：{len(valid)} 个，杀死 {len(killed)} 个，存活 {len(survived)} 个\n")
        f.write(f"- **变异分数：{score:.1f}%**\n\n")
        f.write("| 编号 | 变异算子 | 变异内容 | 结果 |\n| --- | --- | --- | --- |\n")
        for mid, operator, desc, status, _ in results:
            f.write(f"| {mid} | {operator} | {desc} | {status} |\n")
        if survived:
            f.write("\n## 存活变异体分析\n\n")
            for mid, operator, desc, _, summary in survived:
                f.write(f"- **{mid}**（{desc}）：现有用例未区分变异体与原程序，"
                        f"说明该处断言偏弱或缺少针对性用例。\n")
        f.write("\n## 结论\n\n")
        f.write("变异分数反映测试集发现人为缺陷的能力。杀死数越高，说明断言不仅覆盖了代码，"
                "而且真正校验了结果；存活变异体则直接指向需要补强的用例。\n")

    print(f"[OK] {out}")
    print(f"变异分数 {score:.1f}%（{len(killed)}/{len(valid)}）")
    for mid, _, desc, status, _ in results:
        print(f"  {mid} {status}: {desc}")


if __name__ == "__main__":
    main()
