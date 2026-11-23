"""程序插装演示（教材 11.4 ：在程序特定部位插入"探测器"记录动态执行信息）。

与覆盖率工具的区别：
  · 覆盖率只回答"这行有没有被执行"（0/1）；
  · 插装可以回答"这行被执行了多少次"，用于发现**热点**与**从未走过的路径**。

实现方式：`sys.settrace` 在每行代码执行前回调，等价于在每行前插入
`count[line] += 1` 的记录语句（教材所称的"探测器/监控"），无需修改被测源码。

用法：
    python scripts/instrument_demo.py
输出：
    reports/instrumentation_report.md
"""
from __future__ import annotations

import ast
import os
import sys
from collections import Counter
from datetime import date, timedelta

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, BASE)

from app.services.appointment_rules import (  # noqa: E402
    AppointmentContext,
    validate_new_appointment,
)

TARGET = os.path.join(BASE, "app", "services", "appointment_rules.py")
TODAY = date(2026, 11, 23)


def run_scenarios():
    """一组覆盖全部判定的场景（与白盒用例等价）。"""
    ctx_ok = AppointmentContext(service_online=True, capacity=3, used=1)
    ctx_full = AppointmentContext(service_online=True, capacity=1, used=1)
    ctx_dup = AppointmentContext(service_online=True, capacity=5, used=0, has_duplicate=True)
    ctx_off = AppointmentContext(service_online=False, capacity=5, used=0)

    cases = [
        (ctx_ok, TODAY + timedelta(days=1), "09:00-10:00"),
        (ctx_ok, TODAY, "09:00-10:00"),
        (ctx_ok, TODAY - timedelta(days=1), "09:00-10:00"),
        (ctx_ok, TODAY + timedelta(days=31), "09:00-10:00"),
        (ctx_ok, None, "09:00-10:00"),
        (ctx_ok, TODAY + timedelta(days=1), "25:00-26:00"),
        (ctx_dup, TODAY + timedelta(days=1), "09:00-10:00"),
        (ctx_full, TODAY + timedelta(days=1), "09:00-10:00"),
        (ctx_off, TODAY + timedelta(days=1), "09:00-10:00"),
    ]
    for ctx, day, slot in cases:
        validate_new_appointment(ctx, day, slot, today=TODAY)

    # 额外覆盖"不注入 today → 取系统日期"的默认分支（插装要求每条语句都走到）
    validate_new_appointment(ctx_ok, date.today() + timedelta(days=1), "09:00-10:00")


def instrument(func, target_file):
    """插装：统计 target_file 中每一行被执行的次数。"""
    counts = Counter()
    target = os.path.abspath(target_file)

    def tracer(frame, event, arg):
        if os.path.abspath(frame.f_code.co_filename) != target:
            return None
        if event == "line":
            counts[frame.f_lineno] += 1
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        func()
    finally:
        sys.settrace(old)
    return counts


def executable_lines(path, func_name="validate_new_appointment"):
    """用 AST 收集**目标函数体内**可执行语句的起始行号（不含注释、空行、docstring）。

    模块级语句（import、类/常量定义）只在导入时执行一次，不属于被测单元，
    故排除在外，避免把"导入开销"误读成"未覆盖代码"。
    """
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)

    target = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == func_name),
        None,
    )
    if target is None:
        raise SystemExit(f"未找到函数 {func_name}")
    start, end = target.lineno, target.end_lineno

    docstrings = set()
    for node in ast.walk(target):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(body[0].lineno)

    lines = sorted(
        {node.lineno for node in ast.walk(target) if isinstance(node, ast.stmt)}
        - docstrings
        - {start}
    )
    return source.splitlines(), [ln for ln in lines if start <= ln <= end]


def main():
    run_scenarios()  # 预热，避免首次导入开销混入统计
    counts = instrument(run_scenarios, TARGET)
    source_lines, exec_lines = executable_lines(TARGET)

    hit = [ln for ln in exec_lines if counts.get(ln, 0) > 0]
    dead = [ln for ln in exec_lines if counts.get(ln, 0) == 0]

    rows = []
    for ln in exec_lines:
        text = source_lines[ln - 1].strip()
        rows.append((ln, text, counts.get(ln, 0)))

    out_dir = os.path.join(BASE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "instrumentation_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 程序插装报告（教材 11.4）\n\n")
        f.write(f"- 被插装模块：`app/services/appointment_rules.py`\n")
        f.write(f"- 插装方式：`sys.settrace` 逐行回调（等价于在每行前插入计数器语句）\n")
        f.write(f"- 场景数：9（覆盖 7 个判定的真/假分支）\n")
        f.write(f"- 可执行语句数：{len(exec_lines)}，被执行：{len(hit)}，未执行：{len(dead)}\n")
        f.write(f"- 语句插装覆盖率：{len(hit) / len(exec_lines) * 100:.1f}%\n\n")
        f.write("## 逐行执行次数（探测器读数）\n\n")
        f.write("| 行号 | 语句 | 执行次数 |\n| --- | --- | --- |\n")
        for ln, text, cnt in rows:
            safe = text.replace("|", "\\|")
            f.write(f"| {ln} | `{safe}` | {cnt} |\n")
        if dead:
            f.write("\n## 未执行语句\n\n")
            for ln in dead:
                f.write(f"- 第 {ln} 行：`{source_lines[ln - 1].strip()}`\n")
        else:
            f.write("\n**结论**：本场景集覆盖了模块内全部可执行语句，无未执行语句（死代码 0 处）。\n")

    print(f"[OK] {out}")
    print(f"可执行语句 {len(exec_lines)}，已执行 {len(hit)}，覆盖率 {len(hit) / len(exec_lines) * 100:.1f}%")
    top = counts.most_common(5)
    print("执行次数最高的行：", [(ln, c) for ln, c in top])


if __name__ == "__main__":
    main()
