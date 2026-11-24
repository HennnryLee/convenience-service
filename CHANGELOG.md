# 变更记录（Changelog）

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循语义化版本。课程实验阶段的提交同时记录在 `docs/11-交付清单.md`。

## [1.2.3] - 2026-11-24

### 修复
- **角色边界一致性**：管理员不再能启用/禁用其他管理员；用户列表对管理员不显示操作按钮，
  管理员账号统一走个人中心/CLI。
- **统计口径**：后台“注册用户”只统计普通用户，不再把管理员算入消费者数量。
- **下架服务可见性**：`get_service_detail` 对下架服务返回 None，直链详情与列表/预约入口一致。
- **取消时间规则**：普通用户不能在“已确认且时段已开始”后取消预约；管理员保留异常处理权限。

### 新增
- `docs/17-角色与功能一致性矩阵.md`：游客/普通用户/管理员 × 全部功能的对照表。
- `tests/functional/test_role_consistency.py` 7 条回归；测试增至 576 条。

## [1.2.2] - 2026-11-24

### 新增
- **课程级忘记密码**：管理员在后台「用户管理」为普通用户设置临时密码。
  - 仅允许重置普通用户；管理员走个人中心/CLI；
  - 复用注册密码策略；管理员看不到原密码；
  - 写审计日志 `user.reset_password`；
  - 不强制下次改密，页面提示用户登录后自行修改（课程简化）。

### 变更
- 用户管理列表增加「重置密码」入口；新增 `/admin/users/<id>/reset-password` 页面。
- 测试增至 576 条；覆盖率保持 100%。

## [1.2.1] - 2026-11-24

### 修复
- **无简介服务导致 `/services/` 500**：`ServiceItem` 新增 `summary` 属性，简介为空时返回
  “暂无简介”，不再对 `None` 直接切片；新增功能测试。
- 搜索栏/审计筛选栏桌面端控件被拉成单列，改为单行 flex 布局（移动端仍自动换行）。

### 变更
- 预约表单从个人资料预填姓名/电话；日期增加 `min/max`；默认日期避开“今天全部已过”，
  默认时段选第一个未过且未满的时段。
- 服务详情页在今日无可约时段时提示，主按钮改为“选择其它日期”。
- 取消预约、服务上下架、用户启停增加 `data-confirm` 确认框（CSP 安全）。
- 搜索/筛选增加 `sr-only` 读屏标签；docs/08 修正“面包屑/二次确认”的不准确描述。
- 测试增至 576 条，语句/分支覆盖率保持 100%。

## [1.2.0] - 2026-11-24

### 新增
- **Flask-Migrate/Alembic 版本化迁移**：`migrations/` 两个版本（初始结构、audit_logs），
  `scripts/check_migration.py` 在临时库上演练迁移链，CI 增加迁移步骤，`docs/16` 说明现有库升级路径。
- **管理员审计日志**：`AuditLog` 模型 / `AuditLogRepository` / `audit_service.record`，
  后台 `/admin/audit-logs` 只读页面，覆盖服务增改/上下架、用户启停、预约状态、公告发布六类动作；
  审计失败降级，不阻断主业务。
- **生产部署配置**：`deploy/gunicorn.conf.py`、`deploy/nginx.conf.template`、
  `deploy/convenience.service.template`、`deploy/render_configs.py`、`requirements-prod.txt`。
- **运维增强**：审计归档 `app/services/audit_archive.py` + `scripts/archive_audit_logs.py`；
  夜间任务 `.github/workflows/nightly.yml`（迁移演练/全量回归/Locust/兼容性）；
  部署模板按环境变量渲染，避免提交真实域名/证书路径。
- **健康检查**：`GET /healthz` 返回数据库可用性，供 Nginx/监控探针使用。
- 测试补充审计日志、健康检查、迁移脚本与 DEF-001 回归，用例增至 576 条。

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
