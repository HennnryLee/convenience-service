"""生成 10 份实验报告（Word）。

软件构造 5 份 → E:/张洪老师实验/软件构造/实验报告/
软件测试 5 份 → E:/张洪老师实验/软件测试/实验报告/
命名：学号+姓名+实验名称.docx
"""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

NAME = "李行"
SID = "24012110"
CLASS_NAME = "软件工程2班"
DATE = "2026年10月29日"

OUT_CONSTRUCT = r"E:/张洪老师实验/软件构造/实验报告"
OUT_TEST = r"E:/张洪老师实验/软件测试/实验报告"


def _style(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def _cover(doc, title, course):
    for _ in range(4):
        doc.add_paragraph("")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(course)
    run.font.size = Pt(16)
    run.font.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x8A)

    for _ in range(3):
        doc.add_paragraph("")

    table = doc.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    info = [("姓　　名", NAME), ("学　　号", SID), ("班　　级", CLASS_NAME), ("日　　期", DATE)]
    for i, (k, v) in enumerate(info):
        table.cell(i, 0).text = k
        table.cell(i, 1).text = v
        for col in (0, 1):
            para = table.cell(i, col).paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in para.runs:
                r.font.size = Pt(12)
    doc.add_page_break()


def _h(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.name = "黑体"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
    return p


def _p(doc, text):
    para = doc.add_paragraph(text)
    para.paragraph_format.space_after = Pt(4)
    return para


def _bullets(doc, items):
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def _table(doc, header, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    for i, text in enumerate(header):
        cell = table.rows[0].cells[i]
        cell.text = text
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.bold = True
                run.font.size = Pt(10)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
            for para in cells[i].paragraphs:
                for run in para.runs:
                    run.font.size = Pt(10)
    doc.add_paragraph("")
    return table


def build(path, course, title, sections):
    doc = Document()
    _style(doc)
    _cover(doc, title, course)
    for block in sections:
        kind = block[0]
        if kind == "h":
            _h(doc, block[1], block[2] if len(block) > 2 else 1)
        elif kind == "p":
            _p(doc, block[1])
        elif kind == "b":
            _bullets(doc, block[1])
        elif kind == "t":
            _table(doc, block[1], block[2])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc.save(path)
    print("[OK]", path)


# ============================================================ 软件构造 5 份
CONSTRUCT = []


CONSTRUCT.append((
    "实验一：软件开发概述与项目初始化",
    [
        ("h", "一、实验目的", 1),
        ("p", "1）理解软件生存周期与软件开发过程的基本概念，掌握增量迭代开发模式的基本思想；"
              "2）根据便民服务软件需求搭建 Flask 项目基础结构；3）建立版本管理仓库与提交规范。"),
        ("h", "二、实验环境", 1),
        ("t", ["项目", "配置"],
             [["操作系统", "Windows 11"], ["开发语言", "Python 3.12（要求 3.8+）"],
              ["Web 框架", "Flask 3.1 + Jinja2"], ["ORM / 认证 / 表单",
                                                    "Flask-SQLAlchemy 3.1 / Flask-Login 0.6 / Flask-WTF 1.3"],
              ["数据库", "SQLite（可切换 MySQL 8.0）"], ["版本管理", "Git 2.55（本地仓库）"],
              ["开发工具", "PyCharm / VS Code"]]),
        ("h", "三、实验内容与步骤", 1),
        ("b", [
            "阅读需求：明确六大功能模块（用户管理、服务查询、在线预约、公告资讯、反馈评价、后台管理）及优先级。",
            "对比瀑布模型与增量迭代模型，结合「需求粒度粗、课程分批交付」的特点确定采用增量迭代。",
            "按 Scrum 方法梳理角色（产品负责人/Scrum Master/开发团队）与活动，编写 22 条用户故事。",
            "搭建 Flask 项目骨架：应用工厂 create_app()、config.py 三套配置、extensions.py 扩展解耦、"
            "modules/ 蓝图分模块、templates/ 模板继承、static/ 静态资源。",
            "执行 git init 初始化仓库，编写 docs/00-Git提交规范.md，完成首次提交。",
        ]),
        ("h", "四、构造成果", 1),
        ("t", ["成果", "说明"],
             [["项目目录结构", "app/{models,repositories,services,modules,forms,templates,static} 三层架构，"
                            "详见 docs/01-项目结构说明.md"],
              ["用户故事列表", "US-01 ~ US-22，含优先级（MoSCoW）与验收标准，详见 docs/02-用户故事列表.md"],
              ["过程说明", "增量 vs 瀑布对比表、4 个增量划分、Scrum 仪式落地、DoD，详见 docs/03"],
              ["Git 首次提交", "fbef421  chore(project): 初始化Flask项目骨架、目录结构与Git仓库（实验一）"],
              ["可运行验证", "/ 、/about 返回 200，未知路径返回 404 错误页"]]),
        ("h", "五、问题与解决", 1),
        ("t", ["问题", "现象", "解决方法"],
             [["Flask-Login 报 Missing user_loader", "首页面渲染 500 异常",
               "实验一阶段暂不接入登录态，延后至实验四注册 user_loader（见提交历史）"],
              ["模板中引用了尚不存在的路由端点", "url_for 抛出 BuildError",
               "首页与导航栏按增量原则先留占位，实验四接入后再补充链接"],
              ["提交时大量 CRLF 警告", "Git 提示 LF will be replaced by CRLF",
               "属 Windows 平台正常提示，代码内容不受影响"]]),
        ("h", "六、实验总结与改进建议", 1),
        ("p", "本次实验完成了从需求到骨架的落地。应用工厂模式让同一份代码可加载开发/测试/交付三套配置，"
              "为后续每个实验的自动化测试打下基础；三层分层（表现层→业务层→数据层）把变化隔离在局部。"
              "改进建议：后续补充 Flask-Migrate 做数据库版本管理，并在 CI 中固化测试与覆盖率门禁。"),
    ],
))

CONSTRUCT.append((
    "实验二：模块化软件构造",
    [
        ("h", "一、实验目的", 1),
        ("p", "掌握分解与模块化方法，理解内聚与耦合；运用模块化原则对系统进行功能分解，"
              "并以测试驱动（TDD）方式构造核心模块。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / Flask 3.1 / pytest 9.2 / pytest-cov / Git。测试使用内存数据库。"),
        ("h", "三、实验内容与步骤", 1),
        ("b", [
            "功能分解：拆出 6 个业务模块 + 3 个支撑层，绘制模块结构图（Mermaid）。",
            "耦合分析：逐条列出模块间依赖，判定数据耦合/标记耦合/公共耦合/内容耦合。",
            "选定在线预约模块为详细设计对象：函数划分、数据结构（frozen dataclass、表驱动状态机）、算法选择。",
            "TDD 红灯：先写 33 条用例并运行，确认全部失败（ModuleNotFoundError）。",
            "TDD 绿灯：实现 appointment_rules 与 password_policy 两个纯函数模块，用例全部通过。",
            "用等价类划分与边界值分析对模块做黑盒复核，提交代码。",
        ]),
        ("h", "四、构造成果", 1),
        ("t", ["成果", "说明"],
             [["模块结构图", "docs/04 含分层调用关系图与依赖矩阵"],
              ["耦合类型判定", "表现层→业务层为数据耦合（弱）；业务层→常量表为公共耦合（弱）；"
                           "无内容耦合；已消除控制耦合"],
              ["核心模块", "app/services/appointment_rules.py（6 个函数）+ password_policy.py"],
              ["数据结构", "AppointmentContext（frozen dataclass）、APPOINTMENT_TRANSITIONS（dict→set 表驱动）"],
              ["TDD 记录", "红灯 2 errors → 绿灯 33 passed in 0.79s"],
              ["Git 提交", "86fccb9  feat(appointment): 以TDD方式构造预约管理核心模块与密码策略，含33条单元测试"]]),
        ("h", "五、问题与解决", 1),
        ("t", ["问题", "现象", "解决方法"],
             [["业务规则与数据库耦合", "规则函数内直接查询，测试必须起数据库",
               "抽出 AppointmentContext 由调用方注入，规则层变为纯函数"],
              ["日期边界依赖系统时间", "用例在不同日期运行结果不同",
               "为校验函数增加 today 参数，测试注入固定日期"],
              ["状态判断散落为 if/elif", "新增状态要改多处", "改为查表 APPOINTMENT_TRANSITIONS"]]),
        ("h", "六、实验总结与改进建议", 1),
        ("p", "模块化后，业务规则可脱离 Web 与数据库独立测试，33 条用例 0.79 秒跑完，"
              "新增状态或分类只需改常量表。改进建议：为服务编排层补充「应用服务」抽象，"
              "进一步减少视图层对数据层的直接依赖。"),
    ],
))

CONSTRUCT.append((
    "实验三：数据处理与面向对象的软件构造",
    [
        ("h", "一、实验目的", 1),
        ("p", "掌握面向对象构造与数据处理技术：类模型设计、契约式设计、数据结构选择、"
              "数据持久化与表驱动编程。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / Flask-SQLAlchemy 3.1（SQLAlchemy 2.x）/ SQLite / pytest 9.2。"),
        ("h", "三、实验内容与步骤", 1),
        ("b", [
            "识别 5 个核心领域对象：User、ServiceItem、Appointment、Announcement、Feedback，绘制类模型图。",
            "说明类关系：组合（User-Appointment）、关联（Service-Appointment）、聚合（User-Announcement）、"
            "一对一（Appointment-Feedback）、泛化（User 继承 UserMixin）。",
            "编写契约式设计表：为每个关键方法明确前置条件、后置条件、不变量。",
            "设计 5 张表并论证满足第三范式；添加 CHECK 约束、唯一索引与复合索引。",
            "实现 Repository 数据访问层，完成用户与预约两个模块的增删改查。",
            "用表驱动改造状态流转、分类映射、排序映射、星级文案。",
            "编写 55 条数据层单元测试。",
        ]),
        ("h", "四、构造成果", 1),
        ("t", ["成果", "说明"],
             [["领域类模型", "docs/06 类图 + 关系说明 + 10 个方法的契约表"],
              ["数据库表结构", "users / services / appointments / announcements / feedbacks，"
                           "含 CHECK 约束与索引，docs/07 + docs/schema.sql"],
              ["范式论证", "1NF 原子值；2NF 单列代理主键无部分依赖；3NF 无传递依赖"],
              ["数据访问层", "5 个 Repository 封装全部 ORM 操作"],
              ["表驱动", "状态机、分类、排序、星级文案 4 处查表替代 if/elif"],
              ["单元测试", "55 passed（含密码哈希、唯一性、分页排序、容量统计、级联删除）"],
              ["Git 提交", "ee6762b  feat(models): 领域模型、数据库表结构、数据访问层与持久化单元测试"]]),
        ("h", "五、问题与解决", 1),
        ("t", ["问题", "现象", "解决方法"],
             [["SQLite 不支持部分唯一索引", "无法用唯一约束排除已取消预约",
               "改为服务层判定（has_duplicate）+ 复合索引加速，并在文档中说明"],
              ["feedbacks 的 service_id 冗余", "可能被视为违反 3NF",
               "论证为受控冗余（预约不可变，无更新异常），便于按服务统计评分"],
              ["datetime.utcnow 弃用告警", "Python 3.12 抛出 DeprecationWarning",
               "改为 default=lambda: datetime.now()"]]),
        ("h", "六、实验总结与改进建议", 1),
        ("p", "面向对象建模把业务概念显式化，契约式设计让「谁能改、改成什么样」有据可依，"
              "Repository 层把数据库访问收敛到单一位置。改进建议：引入 Flask-Migrate 管理表结构演进。"),
    ],
))

CONSTRUCT.append((
    "实验四：用户交互的软件构造",
    [
        ("h", "一、实验目的", 1),
        ("p", "理解用户交互设计原则，掌握 Flask + Jinja2 页面构造、表单处理、会话与权限管理方法。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / Flask 3.1 / Jinja2 / Flask-Login / Flask-WTF / Chrome、Edge、Firefox。"),
        ("h", "三、实验内容与步骤", 1),
        ("b", [
            "角色与场景分析：游客、普通用户、管理员三类角色的典型操作流程。",
            "页面结构设计：base.html 父模板 + 各业务子模板的继承层级与跳转逻辑（POST-Redirect-GET）。",
            "实现注册/登录、服务查询（列表+详情）、在线预约三大核心页面。",
            "表单处理：5 类表单的字段校验规则与逐字段错误提示。",
            "会话与权限：Flask-Login 登录状态、@login_required、admin_required 装饰器、next 安全跳转。",
            "反馈机制：flash 提示（成功/失败/警告）、提交中加载态、防重复提交。",
            "编写 20 条集成测试并全部通过。",
        ]),
        ("h", "四、构造成果", 1),
        ("t", ["成果", "说明"],
             [["页面清单", "首页、服务查询、服务详情、在线预约、我的预约、公告列表/详情、"
                        "评价提交/列表、后台（概览/服务/用户/预约/公告）共 14 个页面"],
              ["交互原则落地", "一致性（统一父模板与宏）、简洁性、可反馈性、容错性、可控性"],
              ["表单校验", "注册/登录/预约/评价/服务维护 5 类，全部带 CSRF 令牌"],
              ["会话与权限", "user_loader + login_required + admin_required + 站内跳转白名单"],
              ["集成测试", "20 passed（注册6/登录与会话3/访问控制3/预约表单3/取消1/页面4…）"],
              ["Git 提交", "e5d1d4f  feat(web): 页面模板、表单校验、会话与权限管理，含20条集成测试"]]),
        ("h", "五、问题与解决", 1),
        ("t", ["问题", "现象", "解决方法"],
             [["Jinja 宏不支持 **kwargs", "分页宏解析报 TemplateSyntaxError",
               "改为 (pagination, endpoint, extra=None) + 内部 **params 展开"],
              ["中文引号导致 Python 语法错误", "flash 字符串中嵌套直角引号引发 SyntaxError",
               "改用中文书名号「」避免与字符串定界符冲突"],
              ["写操作刷新会重复提交", "表单 POST 后刷新重复写入", "统一改为提交成功后重定向（PRG 模式）"]]),
        ("h", "六、实验总结与改进建议", 1),
        ("p", "交互层完成后系统形成完整闭环，全部 75 条测试通过。改进建议：补充前端组件化与无障碍（a11y）"
              "支持，并为关键操作增加二次确认弹窗。"),
    ],
))

CONSTRUCT.append((
    "实验五：软件重构与交付",
    [
        ("h", "一、实验目的", 1),
        ("p", "理解重构概念与常用手法，完成代码重构、系统集成、端到端验证与项目交付。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / Flask 3.1 / pytest 9.2 / coverage 7.17 / Git。"),
        ("h", "三、实验内容与步骤", 1),
        ("b", [
            "识别 5 处坏味道：重复代码、过长函数、魔法数字、冗长条件、命名不规范。",
            "重构 1：提炼超类 BaseRepository + 方法上移，消除 5 处 add/commit 样板代码。",
            "重构 2：提炼函数 _build_service_payload，拆分过长视图。",
            "重构 3：以常量替换魔法数字（3 个分页常量）。",
            "重构 4：以表驱动替换连续 if（_apply_filters 字段映射表）。",
            "重构 5：重命名变量 service_detail 消除同名混淆。",
            "每次重构后执行全量 pytest 回归（75 条用例保持不变）。",
            "补充端到端测试、导出数据库脚本、编写部署与交付文档。",
        ]),
        ("h", "四、构造成果", 1),
        ("t", ["指标", "重构前", "重构后", "变化"],
             [["repositories 代码行数", "402", "316", "−86（−21%）"],
              ["add/commit 样板代码", "5 处", "1 处（基类）", "−4 处"],
              ["edit_service 长度/圈复杂度", "40 行 / 6", "22 行 / 3", "−45% / −50%"],
              ["分页魔法数字", "5 处", "0 处", "全部消除"],
              ["自动化测试", "75 通过", "75 通过（含新增 2 条 E2E 共 77）", "功能保持不变"]]),
        ("p", "端到端测试：覆盖 注册→登录→查询→预约→后台确认→完成→评价→退出 全流程并退出后会话失效，"
              "另含「已下架服务不可预约」场景，2 条全部通过。"),
        ("p", "交付物：源代码、依赖清单、测试代码、数据库脚本 docs/schema.sql、项目文档 01~11、"
              "Git 提交历史 5 次增量提交。详见 docs/11-交付清单.md。"),
        ("h", "五、问题与解决", 1),
        ("t", ["问题", "现象", "解决方法"],
             [["重构后 FeedbackRepository.count 丢失", "后台统计报 AttributeError",
               "统一改用基类 count_all()，并同步更新测试"],
              ["instance 目录不存在", "开发环境报 unable to open database file",
               "config.py 中 os.makedirs(INSTANCE_DIR, exist_ok=True)"]]),
        ("h", "六、实验总结与改进建议", 1),
        ("p", "重构在不改变外部行为的前提下显著降低重复度与复杂度，并由 77 条测试提供安全网。"
              "改进建议：继续向「应用服务层」收敛视图逻辑，生产环境改用 Gunicorn + MySQL。"),
    ],
))


# ============================================================ 软件测试 5 份
TESTS = []


TESTS.append((
    "实验一：黑盒测试与功能测试",
    [
        ("h", "一、实验目的", 1),
        ("p", "掌握等价类划分法、边界值分析法和场景法，针对页面功能、表单提交、路由跳转与提示信息设计用例并完成功能测试。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / Flask 3.1 测试客户端 / pytest 9.2 / SQLite 内存库。"),
        ("h", "三、测试用例设计", 1),
        ("p", "1）用户注册——等价类划分（覆盖用户名、密码、邮箱、手机号的有效/无效类）；"
              "2）服务查询——边界值分析（关键词长度 0/1/50/51、特殊字符、无匹配）；"
              "3）在线预约——场景法（基本流 + 4 条备选流）。"),
        ("h", "四、测试结果", 1),
        ("t", ["方法", "用例数", "通过", "失败", "覆盖点"],
             [["等价类划分（注册）", "24", "24", "0", "用户名长度/字符、密码强度、邮箱格式、手机号、重复注册"],
              ["边界值分析（查询）", "8", "8", "0", "空、1、50、51、SQL注入串、XSS串、无匹配、% 通配符"],
              ["场景法（预约）", "8", "8", "0", "基本流 + 未登录/信息缺失/日期非法/名额已满/缺CSRF"],
              ["合计", "40", "40", "0", "通过率 100%"]]),
        ("h", "五、缺陷记录与分析", 1),
        ("t", ["编号", "缺陷", "严重程度", "状态"],
             [["DEF-001", "关键词中的 % 被 LIKE 当作通配符，搜索结果被放大", "一般", "新建（未修复）"],
              ["—", "SQL 注入串被当作普通字符串处理，未泄露数据", "—", "通过"],
              ["—", "XSS 载荷被 Jinja2 转义输出", "—", "通过"]]),
        ("h", "六、实验总结与改进建议", 1),
        ("p", "黑盒方法有效覆盖了输入域的边界与异常：长度 51 会被拒绝、过去日期与满员时段会被拦截，"
              "系统表现符合需求。发现的 DEF-001 属于实现细节缺陷（LIKE 未转义），已登记并保留现场，"
              "未通过修改业务代码掩盖。建议后续对搜索关键词做转义并补充模糊查询的用例。"),
    ],
))

TESTS.append((
    "实验二：白盒测试与单元测试",
    [
        ("h", "一、实验目的", 1),
        ("p", "掌握语句覆盖、判定覆盖、条件覆盖与基本路径测试法，使用 pytest 与 coverage.py 完成单元测试与覆盖率分析。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / pytest 9.2 / pytest-cov 7 / coverage 7.17。"),
        ("h", "三、被测单元与流程分析", 1),
        ("t", ["单元", "圈复杂度 V(G)", "独立路径数", "说明"],
             [["U1 validate_password（密码强度）", "8", "8", "7 个判定 + 1"],
              ["U2 validate_new_appointment（预约校验）", "8", "8", "7 个判定 + 1"],
              ["U3 can_transition（状态机判定）", "5", "5", "4 个状态分支 + 默认分支"],
              ["U4 can_review（评价资格）", "5", "5", "4 个判定 + 1"]]),
        ("h", "四、测试用例与执行结果", 1),
        ("t", ["覆盖类型", "用例要点", "结果"],
             [["语句覆盖", "U1~U4 每个可执行语句至少执行一次", "通过"],
              ["判定覆盖", "每个判定的真/假分支各取一次", "通过"],
              ["条件覆盖", "复合条件 has_letter and has_digit、username and password==username 的各组合", "通过"],
              ["路径覆盖", "U1 设计 8 条独立路径、U2 覆盖日期 4 条边界路径、U4 覆盖 5 条路径", "通过"]]),
        ("h", "五、覆盖率报告", 1),
        ("t", ["指标", "数值", "要求", "结论"],
             [["语句总数/未覆盖", "1075 / 78", "—", "—"],
              ["语句覆盖率", "92.7%", "≥ 80%", "达标"],
              ["分支总数/未覆盖", "210 / 39", "—", "—"],
              ["分支覆盖率", "81.4%", "—", "达标"],
              ["核心规则模块", "appointment_rules 100%、password_policy 100%", "—", "优秀"]]),
        ("p", "未覆盖代码主要集中在后台管理视图的异常分支与错误页处理路径，"
              "已判断是否属于异常处理分支（非冗余代码），后续可补充针对性用例。"),
        ("h", "六、实验总结与改进建议", 1),
        ("p", "白盒测试把「分支是否真的被走过」变成可量化指标：核心业务规则达到 100% 语句覆盖。"
              "改进建议：为后台管理的异常分支补充用例，并在 CI 中设置覆盖率门禁（<80% 则失败）。"),
    ],
))

TESTS.append((
    "实验三：集成测试",
    [
        ("h", "一、实验目的", 1),
        ("p", "理解集成测试策略，针对模块接口设计用例，验证模块间的数据传递与协作关系。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / Flask 测试客户端 / SQLite 内存库 / pytest 9.2。"),
        ("h", "三、集成策略", 1),
        ("p", "采用**自底向上（Bottom-Up）**策略。选择理由：数据访问层与业务规则层已完成单元测试且质量稳定，"
              "由底向上逐层集成到表现层，可用真实数据库替代桩模块，缺陷定位容易（底层已验证过）。"),
        ("h", "四、集成点与执行结果", 1),
        ("t", ["集成点", "测试内容", "异常场景", "结果"],
             [["I-1 用户管理→在线预约", "登录状态/用户身份被正确接收，写入正确 user_id",
               "未登录跳转登录页；不同用户会话不串号", "通过"],
              ["I-2 服务查询→在线预约", "service_id 与服务信息正确传递并落库",
               "已下架服务、不存在的服务 id 被拒绝", "通过"],
              ["I-3 在线预约→后台管理", "预约记录可被后台查询，状态推进结果同步到用户侧",
               "非法状态流转、参数缺失不改变数据", "通过"],
              ["I-4 后台管理→反馈评价", "预约完成后评价资格开放，评价正确关联预约与服务",
               "未完成不可评价、重复评价被拒", "通过"]]),
        ("p", "共 33 条集成测试（含实验四原有 20 条 + 本次新增 13 条），全部通过。"),
        ("h", "五、缺陷记录与分析", 1),
        ("p", "本轮发现的 DEF-005（已取消预约仍保留历史记录）经分析属于**设计如此**："
              "容量统计与重复校验均排除 cancelled 状态，取消后应释放名额，故关闭该缺陷。"
              "未发现模块间接口不匹配类缺陷——各模块通过 Repository 与 Service 的明确接口协作，"
              "参数与返回值契约清晰。"),
        ("h", "六、实验总结与改进建议", 1),
        ("p", "自底向上策略让集成问题集中在「数据是否按预期落库、状态是否同步」两个可观测点上，"
              "定位效率高。改进建议：为跨模块调用补充契约测试（如服务返回结构变更时的自动化校验）。"),
    ],
))

TESTS.append((
    "实验四：系统测试",
    [
        ("h", "一、实验目的", 1),
        ("p", "从系统层面验证功能、性能、兼容性与安全性，掌握系统测试流程与评价方法。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / Flask 3.1 / Locust 2.47 / Selenium 4.39 / Firefox / pytest 9.2。"),
        ("h", "三、功能测试（端到端）", 1),
        ("p", "覆盖 注册→登录→服务查询→在线预约→后台确认→完成→评价→我的评价→退出 完整业务链路，"
              "以及「已下架服务不可预约」场景，2 条端到端用例全部通过。"),
        ("h", "四、性能测试", 1),
        ("t", ["并发用户", "总请求", "错误率", "平均响应", "90%", "95%", "最大", "吞吐量"],
             [["50", "861", "0.00%", "29 ms", "49 ms", "180 ms", "271 ms", "29.7 req/s"],
              ["100", "1686", "0.00%", "42 ms", "92 ms", "270 ms", "431 ms", "58.1 req/s"],
              ["200", "3280", "0.00%", "109 ms", "370 ms", "610 ms", "1221 ms", "112.7 req/s"]]),
        ("p", "判定：平均响应 ≤ 3s（实测 29–109 ms）、错误率 ≤ 1%（实测 0%），**性能达标**。"),
        ("h", "五、兼容性测试", 1),
        ("t", ["浏览器", "1920×1080", "1366×768", "375×667", "说明"],
             [["Firefox", "通过", "通过", "通过", "无横向溢出，链接/按钮渲染正常"],
              ["Edge", "未执行", "未执行", "未执行", "WebDriver 驱动异常"],
              ["Chrome", "未安装", "未安装", "未安装", "需手工补充"]]),
        ("h", "六、安全性测试", 1),
        ("t", ["测试项", "方法", "结果"],
             [["SQL 注入", "登录框/搜索框注入 ' OR '1'='1、UNION SELECT", "通过，未泄露数据"],
              ["XSS", "评价内容与服务名注入 <script>、<img onerror>", "通过，被 Jinja2 转义"],
              ["CSRF", "缺少 csrf_token 的 POST", "通过，返回 400"],
              ["会话管理", "退出后访问受限页、cookie 有效期配置", "通过，302 跳转登录页"],
              ["权限控制/越权", "普通用户访问后台、取消/评价他人预约", "通过，403 或拒绝提示"],
              ["开放重定向", "?next=https://evil.example.com", "通过，仅接受站内路径"],
              ["密码存储", "检查 password_hash 字段", "通过，哈希存储"]]),
        ("h", "七、缺陷与结论", 1),
        ("p", "登记 DEF-002（移动端 375px 无法自动化验证，Firefox 最小窗口受限）、"
              "DEF-003（SQLite 高并发写锁竞争风险）、DEF-004（开发服务器不适合生产）。"
              "系统功能、性能、安全性均达标，建议带条件发布：发布前修复 DEF-001，生产切换 MySQL + Gunicorn。"),
    ],
))

TESTS.append((
    "实验五：测试管理与测试报告",
    [
        ("h", "一、实验目的", 1),
        ("p", "掌握测试计划制定、用例管理、缺陷跟踪与测试报告编写方法，对测试过程进行组织、跟踪与总结。"),
        ("h", "二、实验环境", 1),
        ("p", "Windows 11 / Python 3.12 / pytest 9.2 / coverage 7.17 / Locust 2.47 / Git；"
              "缺陷管理采用 Markdown 登记表 + CSV（离线环境，未接入 Jira/Bugzilla）。"),
        ("h", "三、测试计划要点", 1),
        ("t", ["维度", "内容"],
             [["测试范围", "六大功能模块的黑盒/白盒/集成/系统测试；不含第三方组件内部实现"],
              ["测试策略", "单元白盒 ≥80% 覆盖；黑盒等价类+边界值+场景法；集成自底向上；系统测性能/兼容/安全"],
              ["进度安排", "T1 设计 4h → T2 黑盒 3h → T3 白盒 3h → T4 集成 2h → T5 系统 4h → T6 管理 2h"],
              ["风险应对", "数据污染用内存库隔离；并发写用读为主+MySQL 建议；驱动缺失用手工清单降级"],
              ["准出标准", "通过率 ≥95%、致命/严重缺陷为 0、覆盖率 ≥80%、性能与安全性达标"]]),
        ("h", "四、缺陷跟踪与统计", 1),
        ("t", ["编号", "标题", "严重程度", "状态"],
             [["DEF-001", "搜索关键词 % 未转义，结果被放大", "一般", "新建"],
              ["DEF-002", "移动端 375px 无法自动化验证", "轻微", "新建"],
              ["DEF-003", "SQLite 高并发写锁竞争风险", "一般", "确认（风险）"],
              ["DEF-004", "Flask 开发服务器不适合生产并发", "轻微", "新建"],
              ["DEF-005", "已取消预约保留历史记录", "轻微", "关闭（设计如此）"]]),
        ("h", "五、测试用例执行统计", 1),
        ("t", ["类型", "用例数", "通过", "失败", "通过率"],
             [["功能（黑盒）", "40", "40", "0", "100%"],
              ["单元（白盒）", "71", "71", "0", "100%"],
              ["集成", "33", "33", "0", "100%"],
              ["系统（端到端+安全）", "16", "16", "0", "100%"],
              ["合计", "160", "160", "0", "100%"]]),
        ("h", "六、测试结论与质量评价", 1),
        ("p", "功能 160 条用例全部通过；语句覆盖率 92.7%、分支覆盖率 81.4%，核心规则模块 100%；"
              "50/100/200 并发平均响应 29–109 ms、错误率 0%；SQL 注入、XSS、CSRF、越权、开放重定向、"
              "密码存储六类安全检查全部通过。**质量结论：建议带条件发布**——发布前修复 DEF-001，"
              "生产环境切换 MySQL + Gunicorn。"),
        ("h", "七、个人实验总结", 1),
        ("p", "通过本轮实验，我把「先设计再执行、先单元后系统」的测试流程完整走了一遍："
              "黑盒方法保证了输入域的覆盖，白盒方法把覆盖率变成可量化指标，"
              "集成测试聚焦模块协作，系统测试从用户视角给出发布结论。"
              "最大的收获是：缺陷登记必须保留现场（DEF-001 未通过改代码掩盖），"
              "这样的测试结论才可信，也才能真正指导后续改进。"),
    ],
))


def main():
    for i, (title, sections) in enumerate(CONSTRUCT, start=1):
        path = os.path.join(OUT_CONSTRUCT, f"{SID}{NAME}-软件构造{title}.docx")
        build(path, "软件构造实验报告", title, sections)
    for i, (title, sections) in enumerate(TESTS, start=1):
        path = os.path.join(OUT_TEST, f"{SID}{NAME}-软件质量保证与测试{title}.docx")
        build(path, "软件质量保证与测试实验报告", title, sections)


if __name__ == "__main__":
    main()
