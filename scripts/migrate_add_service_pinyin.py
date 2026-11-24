"""为 services 表新增 name_pinyin 列并回填拼音排序键（幂等）。

背景：SQLite 默认 BINARY 排序规则比较的是 UTF-8 字节，中文排出来是 Unicode
码点序（住 U+4F4F → 儿 U+513F → 家 U+5BB6 …），既不是拼音也不是笔画，用户
看到"按名称"排成这样会认为功能坏了。修复方式见 app/utils/pinyin.py。

安全性（吸取此前真实数据被清空的教训）：
  - 只执行 ALTER TABLE ADD COLUMN、CREATE INDEX 与 UPDATE，不删除任何数据；
  - 可重复执行：列/索引已存在则跳过，拼音键已正确则不写；
  - 结束打印各表行数，便于人工核对数据未丢失。

用法： python scripts/migrate_add_service_pinyin.py
"""
from __future__ import annotations

import os
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, BASE)

from sqlalchemy import inspect, select, text  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.service import ServiceItem  # noqa: E402
from app.utils.pinyin import to_pinyin_key  # noqa: E402

COLUMN = "name_pinyin"
INDEX = "ix_services_name_pinyin"
COUNTED_TABLES = ("users", "services", "appointments", "announcements", "feedbacks")


def _columns(inspector, table):
    return {c["name"] for c in inspector.get_columns(table)}


def _indexes(inspector, table):
    return {i["name"] for i in inspector.get_indexes(table)}


def main():
    app = create_app("development")
    with app.app_context():
        inspector = inspect(db.engine)
        if "services" not in inspector.get_table_names():
            print("services 表不存在，请先执行： python run.py --init-db")
            return 1

        added = []

        if COLUMN not in _columns(inspector, "services"):
            db.session.execute(
                text(f"ALTER TABLE services ADD COLUMN {COLUMN} VARCHAR(255) NOT NULL DEFAULT ''")
            )
            db.session.commit()
            added.append(f"services.{COLUMN}")
            inspector = inspect(db.engine)

        if INDEX not in _indexes(inspector, "services"):
            db.session.execute(text(f"CREATE INDEX {INDEX} ON services ({COLUMN})"))
            db.session.commit()
            added.append(INDEX)

        services = list(db.session.scalars(select(ServiceItem).order_by(ServiceItem.id)))
        changed = 0
        for service in services:
            expected = to_pinyin_key(service.name)
            if service.name_pinyin != expected:
                service.name_pinyin = expected
                changed += 1
        if changed:
            db.session.commit()

        print(f"结构变更：{'、'.join(added) if added else '无（已是最新）'}")
        print(f"回填拼音键：{changed} 条 / 共 {len(services)} 条服务")
        for service in services:
            print(f"  [{service.id}] {service.name} -> {service.name_pinyin or '(空)'}")

        print("数据量核对（应与执行前一致）：")
        for table in COUNTED_TABLES:
            count = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
