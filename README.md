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
pytest                                   # 全部测试
pytest tests/unit --cov=app --cov-report=term-missing   # 单元测试 + 覆盖率
```

## 目录与文档
- 目录结构：`docs/01-项目结构说明.md`
- 需求：`docs/02-用户故事列表.md`
- 过程：`docs/03-开发过程选择与Scrum说明.md`
- 设计：`docs/04-领域模型与契约式设计.md`、`docs/05-数据库设计说明.md`
- 交付：`docs/06-部署与运行说明.md`、`docs/07-重构记录.md`、`docs/08-交付清单.md`
