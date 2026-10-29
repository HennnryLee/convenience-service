"""数据库脚本生成工具：把当前模型的建表语句导出为 docs/schema.sql。

用法：python scripts/generate_schema.py
目的：交付时提供可直接在 MySQL/SQLite 中执行的数据库脚本，便于评阅与部署。
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from sqlalchemy.schema import CreateTable  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

OUTPUT = os.path.join(os.path.dirname(__file__), os.pardir, "docs", "schema.sql")


def main():
    app = create_app("development")
    with app.app_context():
        lines = [
            "-- 便民服务平台 数据库脚本",
            "-- 由 scripts/generate_schema.py 自动生成（SQLite 语法）",
            "-- 目标数据库：SQLite；切换 MySQL 时把 INTEGER PRIMARY KEY 改为 INT AUTO_INCREMENT PRIMARY KEY",
            "",
        ]
        for table in db.metadata.sorted_tables:
            lines.append(str(CreateTable(table).compile(db.engine)).strip() + ";")
            lines.append("")
        os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[OK] 已生成 {os.path.abspath(OUTPUT)}")


if __name__ == "__main__":
    main()
