"""审计日志归档命令。

用法：
    # 只导出（默认，安全）
    python scripts/archive_audit_logs.py --before 2026-01-01

    # 导出并删除已归档记录（会二次确认提示）
    python scripts/archive_audit_logs.py --before 2026-01-01 --delete

    # 指定输出文件
    python scripts/archive_audit_logs.py --before 2026-01-01 --output instance/audit-2026.csv

建议：先导出、检查 CSV，再执行 --delete；生产库操作前先备份（docs/16）。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from app import create_app
from app.services.audit_archive import archive_logs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="审计日志归档")
    parser.add_argument("--before", required=True, help="截止日期 YYYY-MM-DD（不含当天）")
    parser.add_argument(
        "--output",
        default=None,
        help="输出 CSV 路径（默认 instance/audit_archive_<before>.csv）",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="导出成功后删除截止日期之前的记录（默认只导出）",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cutoff = datetime.strptime(args.before, "%Y-%m-%d")
    except ValueError:
        print("[FAIL] --before 必须是 YYYY-MM-DD")
        return 2

    output = args.output or os.path.join(
        "instance", f"audit_archive_{cutoff.strftime('%Y%m%d')}.csv"
    )
    app = create_app(os.environ.get("FLASK_CONFIG", "development"))
    with app.app_context():
        result = archive_logs(cutoff, output, remove=args.delete)
    print(f"[OK] 已导出 {result['exported']} 条到 {output}")
    if args.delete:
        print(f"[OK] 已删除 {result['deleted']} 条已归档记录")
    else:
        print("[INFO] 未删除记录；确认 CSV 无误后可加 --delete 重跑")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
