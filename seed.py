"""演示数据脚本（兼容入口）。

实际数据定义已下沉到 ``app/seed_data.py``，便于 CLI、测试与应用工厂复用。
保留本文件是为了不破坏课程文档与历史命令：``python seed.py`` 仍可运行。
"""
from app.seed_data import ANNOUNCEMENTS, SERVICES, seed_demo_data

__all__ = ["SERVICES", "ANNOUNCEMENTS", "seed_demo_data"]


if __name__ == "__main__":
    from app import create_app
    from app.extensions import db
    from app.models import User
    from sqlalchemy import func, select

    app = create_app("development")
    with app.app_context():
        db.create_all()
        summary = seed_demo_data()
        total = db.session.scalar(select(func.count()).select_from(User))
        print(f"[OK] 演示数据：{summary}")
        print(f"[OK] 当前用户数：{total}")
        print("演示账号：admin/Admin@123（管理员）、zhangsan/User@123（普通用户）")
