"""数据库迁移演练：在临时 SQLite 库上执行 Alembic upgrade 并校验表结构。

用途：
  - 本地：改完模型/迁移后快速确认迁移链可达；
  - CI：在测试前验证 `flask db upgrade` 能从空库建出全部表（含 audit_logs）。

不触碰 `instance/app.db`，所有操作在临时目录完成。
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "users",
    "services",
    "appointments",
    "announcements",
    "feedbacks",
    "audit_logs",
    "alembic_version",
}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="convenience-migrate-") as tmp:
        db_path = Path(tmp) / "migration_check.db"
        env = os.environ.copy()
        env.update(
            {
                "FLASK_APP": "app:create_app",
                "FLASK_CONFIG": "development",
                "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
            }
        )
        result = subprocess.run(
            [sys.executable, "-m", "flask", "db", "upgrade"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("[FAIL] flask db upgrade 失败")
            print(result.stdout)
            print(result.stderr)
            return 1

        connection = sqlite3.connect(db_path)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        finally:
            connection.close()

        missing = sorted(EXPECTED_TABLES - tables)
        if missing:
            print(f"[FAIL] 迁移后缺少表：{missing}")
            return 1
        print(f"[OK] 迁移链可达，当前版本：{version[0] if version else 'unknown'}")
        print(f"[OK] 表结构完整：{', '.join(sorted(tables))}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
