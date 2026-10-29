"""应用启动入口。

用法：
    python run.py                 # 开发环境启动 http://127.0.0.1:5000
    python run.py --init-db       # 初始化数据库表结构
    python run.py --seed          # 写入演示数据（服务、公告、管理员账号）
    python run.py --init-db --seed --serve   # 初始化后继续启动服务器
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
    parser.add_argument("--init-db", action="store_true", help="初始化数据库表")
    parser.add_argument("--seed", action="store_true", help="写入演示数据")
    parser.add_argument("--serve", action="store_true", help="初始化后继续启动服务器")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    app = create_app(args.config)

    if args.init_db or args.seed:
        with app.app_context():
            db.drop_all()
            db.create_all()
            print("[OK] 数据库表结构已创建")
            if args.seed:
                from seed import seed_demo_data

                seed_demo_data()
                print("[OK] 演示数据已写入")
        # 仅做初始化/灌数据时不再启动服务器，方便脚本化执行
        if not args.serve:
            return 0

    app.run(host=args.host, port=args.port, debug=app.config.get("DEBUG", False))
    return 0


if __name__ == "__main__":
    main(sys.argv[1:])
