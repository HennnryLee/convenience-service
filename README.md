# 便民服务平台（Convenience Service Platform）

《软件构造》与《软件质量保证与测试》两门课程共用的**同一套被测系统**：
构造实验负责把它建出来，测试实验负责对它做黑盒/白盒/集成/系统测试。

## 功能模块
用户管理 · 服务查询 · 在线预约 · 公告资讯 · 反馈评价 · 后台管理

## 快速开始
```bash
pip install -r requirements.txt
python run.py --init-db --seed
python run.py
# 浏览器打开 http://127.0.0.1:5000
```
默认账号：管理员 `admin / Admin@123`，普通用户 `zhangsan / User@123`。

## 运行测试
```bash
pytest                                           # 全部测试（77 条）
pytest tests/unit                                # 单元测试
pytest tests/functional                          # 功能测试（黑盒）
pytest tests/integration                         # 集成测试
pytest tests/system                              # 系统测试（端到端/安全）
pytest --cov=app --cov-report=term-missing       # 覆盖率
```

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
| 09 | 重构记录 |
| 10 | 部署与运行说明 |
| 11 | 交付清单 |
| — | `docs/schema.sql` 数据库建表脚本 |
