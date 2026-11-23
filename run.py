"""应用启动入口。

用法：
    python run.py                                  # 开发环境启动 http://127.0.0.1:5000
    python run.py --init-db                        # 建表（幂等，不删除已有数据）
    python run.py --seed                           # 灌演示数据（幂等，同名记录自动跳过）
    python run.py --init-db --seed                 # 首次部署：建表 + 灌演示数据
    python run.py --init-db --seed --serve         # 初始化后继续启动服务器
    python run.py --init-db --seed --force-reset   # ⚠️ 危险：清空并重建（数据不可恢复）

安全约定（2026-11-23 修订）：
    早期版本在 --init-db / --seed 时无条件执行 db.drop_all()，用户按"如何运行"
    执行一遍就会把真实数据全部清空。现改为：默认只建表 / 补数据，绝不删；
    只有显式传入 --force-reset 才允许 drop_all()，并会先打印将要删除的数据量。
"""
import argparse
import sys

from app import create_app
from app.extensions import db


def build_parser():
    parser = argparse.ArgumentParser(description="便民服务平台启动脚本")
    parser.add_argument("--config", default="development", help="配置名称：development/testing/production")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--init-db", action="store_true", help="建表（幂等，不删除已有数据）")
    parser.add_argument("--seed", action="store_true", help="灌演示数据（幂等）")
    parser.add_argument("--serve", action="store_true", help="初始化后继续启动服务器")
    parser.add_argument("--force-reset", action="store_true",
                        help="危险：先 drop_all() 清空数据库再重建，数据不可恢复")
    return parser


def _existing_counts():
    """统计库中现有业务数据，用于 --force-reset 前给出代价提示。"""
    from app.models import Announcement, Appointment, Feedback, ServiceItem, User

    return {
        "users": db.session.query(User).count(),
        "services": db.session.query(ServiceItem).count(),
        "appointments": db.session.query(Appointment).count(),
        "announcements": db.session.query(Announcement).count(),
        "feedbacks": db.session.query(Feedback).count(),
    }


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    app = create_app(args.config)

    if args.init_db or args.seed or args.force_reset:
        with app.app_context():
            if args.force_reset:
                counts = _existing_counts()
                print("=" * 62)
                print("⚠️  --force-reset：即将清空并重建数据库，以下数据将被永久删除：")
                for name, count in counts.items():
                    print(f"      {name}: {count} 条")
                print("      此操作不可恢复。若误执行，请立即停止并联系维护者。")
                print("=" * 62)
                db.drop_all()
                db.create_all()
                print("[OK] 数据库已清空并重建表结构")
            else:
                # create_all() 幂等：表已存在则跳过，绝不删除任何一行数据
                db.create_all()
                if args.init_db:
                    print("[OK] 数据库表结构就绪（未删除已有数据）")

            if args.seed:
                from seed import seed_demo_data

                seed_demo_data()
                print("[OK] 演示数据已写入（同名记录自动跳过，未删除已有数据）")
        # 仅做初始化/灌数据时不再启动服务器，方便脚本化执行
        if not args.serve:
            return 0

    app.run(host=args.host, port=args.port, debug=app.config.get("DEBUG", False))
    return 0


if __name__ == "__main__":
    main(sys.argv[1:])
