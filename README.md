# 便民服务平台（Convenience Service Platform）

《软件构造》与《软件质量保证与测试》两门课程共用的**同一套被测系统**：
构造实验负责把它建出来，测试实验负责对它做黑盒/白盒/集成/系统测试。

## 功能模块

用户管理 · 服务查询 · 在线预约 · 公告资讯 · 反馈评价 · 后台管理

## 快速开始

```bash
pip install -r requirements.txt
python run.py --init-db --seed      # 建表 + 演示数据（幂等，不删除已有数据）
python run.py                       # http://127.0.0.1:5000
```

默认账号：管理员 `admin / Admin@123`，普通用户 `zhangsan / User@123`。

也可以使用 Flask CLI（推荐，与应用同配置）：

```bash
flask --app "app:create_app()" init-db          # 幂等建表（含 audit_logs）
flask --app "app:create_app()" seed-demo
flask --app "app:create_app()" check-db         # 连接/表结构/行数自检
flask --app "app:create_app()" create-admin boss boss@example.com
flask --app "app:create_app()" db upgrade       # 全新库用版本化迁移建表
```

后台管理员可在 `/admin/audit-logs` 查看写操作审计记录；健康检查为 `/healthz`。
已有数据库升级到带审计表的版本请按 `docs/16` 先 `db stamp` 再 `db upgrade`，
或先执行 `python run.py --init-db` 补表（只加表、不删数据）。

> ⚠️ `--init-db --seed` 是幂等的，**不会删除已有数据**。只有 `--force-reset` 会 `drop_all()`，
> 且会先打印将删除的数据量；执行前请备份 `instance/app.db`。

## 运行测试

```bash
pytest                                           # 全部测试（576 条）
pytest -m unit                                   # 按层：unit / functional / integration / system
pytest --cov=app --cov-branch --cov-report=term-missing
python -m ruff check app tests scripts run.py seed.py wsgi.py
python scripts/static_check.py                   # 静态程序分析（教材 5.4.7）
python scripts/check_migration.py                # 在临时库上演练 Alembic 迁移链
```

当前质量指标：

| 指标 | 结果 |
| --- | --- |
| 自动化用例 | 576（unit 357 / functional 136 / integration 33 / system 50） |
| 语句覆盖 / 分支覆盖 | 100% / 100%（CI 门槛 98%） |
| ruff / 静态分析 | 0 问题 / 59 文件 0 问题 |
| 插装 / 变异 | 27/27 = 100% / 12/12 = 100% |
| CI | GitHub Actions，Python 3.10/3.12 双版本；ruff + 静态分析 + 迁移演练 + 分支覆盖率 |
| 生产就绪 | `migrations/` 版本化迁移、`/healthz` 健康检查、`audit_logs` 审计与归档、`deploy/` 模板渲染、`.github/workflows/nightly.yml` 夜间巡检 |

## 项目结构（分层）

```
app/
├── __init__.py        应用工厂（配置→扩展→蓝图→日志/安全→错误页→CLI）
├── config.py          development/testing/production 配置 + Cookie 策略
├── cli.py             init-db / seed-demo / create-admin / check-db
├── errors.py          400/403/404/405/413/500 统一错误页
├── logging.py         request_id、访问日志、滚动文件日志
├── security.py        CSP 与安全响应头
├── seed_data.py       幂等演示数据
├── models/            领域实体 + AuditLog 审计支撑表
├── repositories/      数据访问（CRUD/聚合/分页/审计）
├── services/          业务规则 + 应用服务（search/announcement/home/dashboard/audit）
├── modules/           蓝图视图（只做参数解析、服务调用、渲染）
├── forms/             WTForms 表单校验
└── utils/             常量/契约/表驱动/拼音/时段解析/分页
migrations/            Flask-Migrate 迁移（初始结构 + audit_logs）
deploy/                Gunicorn / Nginx / systemd 生产配置示例
```

生产入口为 `wsgi.py`；工程化说明见 `docs/15`，迁移/审计/部署见 `docs/16`。

## 生成设计图与实验报告

按两本教材符号绘制的 10 张设计图由 `scripts/draw_diagrams.py` 生成，报告生成器会把它们
嵌入对应章节。修改图或报告后按以下顺序重建：

```bash
python scripts/draw_diagrams.py                 # 生成 docs/diagrams/*.png（10 张）
python scripts/generate_experiment_reports.py   # 重新生成 10 份 Word 报告（含图）
```

> 图按教材符号绘制：UML 类图（教材 3.3.1）、E-R 图 / 关系图 / 数据库设计六阶段
> （教材 8.1.2、8.3）、模块结构图（教材 2.3）、页面结构图（教材 5.1 / 5.3）、
> 控制流图与因果图 / 状态迁移图（测试教材 11.3 / 10.3 / 10.4）。
> 若图片缺失，报告生成器会直接报错并提示先运行绘图脚本。

## 文档索引

| 编号 | 文档 |
| --- | --- |
| 00 | Git 提交规范 |
| 01 | 项目结构说明（含技术选型与分层架构） |
| 02 | 用户故事列表（Product Backlog） |
| 03 | 开发过程选择与 Scrum 说明 |
| 04 | 模块结构图与耦合分析 |
| 05 | 核心模块详细设计与 TDD 记录 |
| 06 | 领域模型与契约式设计 |
| 07 | 数据库设计说明 |
| 08 | 用户交互设计说明 |
| 09 | 重构记录（含 2026-11-24 第二轮重构） |
| 10 | 部署与运行说明（CLI/日志/生产部署） |
| 11 | 交付清单 |
| 12 | 契约式编程与断言实践 |
| 13 | 表驱动编程实践 |
| 14 | 静态测试与代码审查记录 |
| 15 | 工程化改进与质量门禁 |
| 16 | 生产部署、数据库迁移与审计日志 |
| 17 | 角色与功能一致性矩阵（管理员/普通用户） |
| — | `docs/schema.sql` 数据库建表脚本 |
| — | `docs/diagrams/` 设计图（10 张 PNG，按教材符号绘制） |

## 变更记录

见 `CHANGELOG.md`。2026-11-24 的 1.1.0 版本完成工程化配置、基础设施、应用服务层、
查询优化与测试体系加固，详见 `docs/15`。
