# 变更记录（Changelog）

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循语义化版本。课程实验阶段的提交同时记录在 `docs/11-交付清单.md`。

## [1.2.0] - 2026-11-24

### 新增
- **Flask-Migrate/Alembic 版本化迁移**：`migrations/` 两个版本（初始结构、audit_logs），
  `scripts/check_migration.py` 在临时库上演练迁移链，CI 增加迁移步骤，`docs/16` 说明现有库升级路径。
- **管理员审计日志**：`AuditLog` 模型 / `AuditLogRepository` / `audit_service.record`，
  后台 `/admin/audit-logs` 只读页面，覆盖服务增改/上下架、用户启停、预约状态、公告发布六类动作；
  审计失败降级，不阻断主业务。
- **生产部署配置**：`deploy/gunicorn.conf.py`、`deploy/nginx.conf.example`、
  `deploy/convenience.service`、`requirements-prod.txt`。
- **健康检查**：`GET /healthz` 返回数据库可用性，供 Nginx/监控探针使用。
- 测试补充审计日志、健康检查、迁移脚本与 DEF-001 回归，用例增至 548 条。

### 修复
- **DEF-001 关闭**：服务/用户/公告三处搜索统一改用 `contains(autoescape=True)`，
  `%`、`_` 按字面量匹配，覆盖 `%`/`_`/`\` 的回归用例；缺陷状态由 Open 迁移到 Close。
- 后台审计页面只读、按动作筛选；旧库缺审计表时给出部署提示。

### 变更
- `run.py` / `check-db` 的统计与缺表检查纳入 `audit_logs`。
- 生产依赖单独拆到 `requirements-prod.txt`；`pyproject.toml` 增加 `prod` 可选依赖。

## [1.1.0] - 2026-11-24

### 新增
- 工程化质量门禁：`pyproject.toml`（pytest 标记、分支覆盖率门槛、ruff 规则）、
  `requirements-dev.txt`、`.pre-commit-config.yaml`、`.editorconfig`、
  `.github/workflows/ci.yml`（Python 3.10/3.12 双版本：ruff + 静态分析 + 分支覆盖率）。
- 应用基础设施：`app/cli.py`（Flask CLI：建表、演示数据、创建管理员、自检）、
  `app/logging.py`（请求 ID、访问日志、滚动文件日志）、`app/errors.py`（统一错误页与异常日志）、
  `app/security.py`（安全响应头、会话 Cookie 策略、禁用账号会话失效）。
- 应用服务层：`dashboard_service`、`search_service`、`announcement_service`、`home_service`，
  视图不再直接拼装查询；新增 `app/utils/time_slots.py`（时段边界单一事实来源）。
- 测试：工厂夹具、按目录自动标记、错误页/日志/安全头/CLI/分页/时间边界/性质测试；
  测试用例数与覆盖率同步提升。

### 变更
- `pytest.ini` 合并入 `pyproject.toml`；覆盖率要求分支模式并设置最低门槛。
- 预约日期窗口、密码长度等业务常量去重；分类计数改为单次聚合查询；
  「可评价预约」改为一次关联查询，消除 N+1。
- 服务名称/邮箱写入时规范化（去首尾空白、邮箱小写），避免大小写重复账号。
- 模板去除内联样式，统一为语义化类名；表单补充 `autocomplete` 与无障碍属性。

### 修复
- 后台编辑服务时未校验重名，改名撞库会返回 500（改为保存前校验并给出提示）。
- 禁用账号的既有会话仍可继续访问（`user_loader` 现在拒绝非启用账号）。
- 登录页「账号已被禁用」分支因服务层提前返回 None 而不可达（调整判定顺序后可正确提示）。

## [1.0.0] - 2026-10-29

### 新增
- 便民服务平台首个可交付版本：用户管理、服务查询、在线预约、公告资讯、反馈评价、后台管理。
- Repository / Service / Blueprint 分层，契约式编程、表驱动状态机、拼音排序。
- 382 条 pytest 用例、10 份实验报告、两本教材 OCR 与教材对齐文档。
