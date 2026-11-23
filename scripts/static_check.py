"""静态程序分析（教材 5.4.7）：不运行程序，扫描源码发现可疑构造。

教材列出的静态分析可发现故障类型，本脚本对应实现其中可自动检查的部分：

| 教材故障类型 | 本脚本检查项 |
| --- | --- |
| 控制故障 | 函数过长（>60 行）、嵌套过深（>4 层）、裸 except |
| 数据故障 | 魔法数字（非 0/1/-1 且未命名）、可变默认参数 |
| 接口故障 | `print()` 调试残留、TODO/FIXME 未处理、`import *` |

用法： python scripts/static_check.py
输出： reports/static_analysis.md
"""
from __future__ import annotations

import ast
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SCAN_ROOT = os.path.join(BASE, "app")
ALLOWED_NUMBERS = {0, 1, 2, -1}  # 2 用于索引/二分等惯用法，其余数字须命名


def iter_py_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def max_nesting(node, depth=0):
    """粗略计算控制结构嵌套深度。"""
    nesting_types = (ast.If, ast.For, ast.While, ast.Try, ast.With)
    deepest = depth
    for child in ast.iter_child_nodes(node):
        child_depth = depth + 1 if isinstance(child, nesting_types) else depth
        deepest = max(deepest, max_nesting(child, child_depth))
    return deepest


def check_file(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    rel = os.path.relpath(path, BASE)
    findings = []

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [(rel, exc.lineno or 0, "语法错误", str(exc))]

    # 1) 函数过长 / 嵌套过深 / 裸 except
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > 60:
                findings.append((rel, node.lineno, "函数过长", f"{node.name} 共 {length} 行（阈值 60）"))
            depth = max_nesting(node)
            if depth > 4:
                findings.append((rel, node.lineno, "嵌套过深", f"{node.name} 嵌套 {depth} 层（阈值 4）"))
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append((rel, node.lineno, "裸 except", "捕获所有异常且未指定类型，可能掩盖缺陷"))

    # 2) 魔法数字：只报告**判定条件中**的硬编码数值（真正的逻辑耦合点），
    #    函数默认参数与配置常量不算（它们本身就是具名参数/常量）。
    if not rel.endswith(("config.py", "constants.py")):
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                operands = [node.left] + list(node.comparators)
                for operand in operands:
                    if isinstance(operand, ast.Constant) and isinstance(operand.value, (int, float)) \
                            and not isinstance(operand.value, bool) \
                            and operand.value not in ALLOWED_NUMBERS:
                        findings.append(
                            (rel, node.lineno, "条件中的魔法数字",
                             f"判定里出现字面量 {operand.value}，建议提取为具名常量")
                        )

    # 3) 可变默认参数
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d]:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append((rel, node.lineno, "可变默认参数", f"{node.name} 使用可变对象作默认值"))

    # 4) print 残留 / import *
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            findings.append((rel, node.lineno, "print 残留", "库代码中不应直接打印到标准输出"))
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            findings.append((rel, node.lineno, "import *", "通配符导入会污染命名空间"))

    # 5) TODO/FIXME
    for lineno, line in enumerate(source.splitlines(), start=1):
        for mark in ("TODO", "FIXME", "XXX"):
            if mark in line:
                findings.append((rel, lineno, f"{mark} 未处理", line.strip()[:80]))

    return findings


def main():
    all_findings = []
    files = sorted(iter_py_files(SCAN_ROOT))
    for path in files:
        all_findings.extend(check_file(path))

    by_type = {}
    for _rel, _line, kind, _detail in all_findings:
        by_type[kind] = by_type.get(kind, 0) + 1

    out_dir = os.path.join(BASE, "reports")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "static_analysis.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 静态程序分析报告（教材 5.4.7）\n\n")
        f.write(f"- 扫描范围：`app/` 共 {len(files)} 个 Python 文件\n")
        f.write(f"- 检查项：函数长度、嵌套深度、裸 except、魔法数字、可变默认参数、print 残留、import *、TODO\n")
        f.write(f"- 发现问题：{len(all_findings)} 处\n\n")
        if by_type:
            f.write("| 问题类型 | 数量 |\n| --- | --- |\n")
            for kind, count in sorted(by_type.items(), key=lambda kv: -kv[1]):
                f.write(f"| {kind} | {count} |\n")
            f.write("\n## 明细\n\n| 文件 | 行 | 类型 | 说明 |\n| --- | --- | --- | --- |\n")
            for rel, line, kind, detail in all_findings[:80]:
                detail = detail.replace("|", "\\|")
                f.write(f"| `{rel}` | {line} | {kind} | {detail} |\n")
            if len(all_findings) > 80:
                f.write(f"\n> 仅显示前 80 条，其余 {len(all_findings) - 80} 条略。\n")
        else:
            f.write("未发现问题。\n")

    print(f"[OK] {out}")
    print(f"扫描 {len(files)} 个文件，发现 {len(all_findings)} 处问题")
    for kind, count in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"  {kind}: {count}")


if __name__ == "__main__":
    main()
