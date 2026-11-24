# -*- coding: utf-8 -*-
"""按《基于案例的软件构造教程》与《软件质量保证与测试（第2版）》的符号规范，
生成实验报告所需的 8 张设计图（PNG）。

设计依据（图面不标注，教材依据见报告正文）：
  - 2.3   模块的内聚性与耦合性            -> 模块结构图
  - 3.3.1 面向对象的设计符号（UML 类图）  -> 类图 / 类关系图
  - 5.1/5.3 用户交互与页面组织            -> 页面结构设计图
  - 8.1.2 关系数据库的数据模型            -> 关系图（图8.1）/ 关系模式
  - 8.3   数据库的开发过程（6 阶段）      -> 数据库设计过程图
  - 8.3   概念结构设计 E-R 模型（图8.10/8.11）-> E-R 图
  - 测试教材 11.3 程序控制流图与圈复杂度  -> 控制流图

运行： python scripts/draw_diagrams.py
输出： docs/diagrams/*.png
"""
from __future__ import annotations

import os
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse, Polygon, FancyArrowPatch, Circle

# ---------------------------------------------------------------- 全局样式
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans SC"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 10

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "diagrams")
os.makedirs(OUT, exist_ok=True)

C = {
    "ink": "#1e293b",
    "muted": "#64748b",
    "line": "#475569",
    "blue_f": "#eff6ff",
    "blue_e": "#1d4ed8",
    "green_f": "#ecfdf5",
    "green_e": "#059669",
    "amber_f": "#fffbeb",
    "amber_e": "#d97706",
    "purple_f": "#f5f3ff",
    "purple_e": "#7c3aed",
    "gray_f": "#f8fafc",
    "gray_e": "#94a3b8",
    "white": "#ffffff",
}


def canvas(w, h, title=None, subtitle=None):
    fig, ax = plt.subplots(figsize=(w / 1.6, h / 1.6))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    if title:
        # 标题放在坐标系上方留白区，避免与顶部内容（图例/接口框/属性椭圆）重叠
        ax.text(w / 2, h + 0.72, title, ha="center", va="center",
                fontsize=14, fontweight="bold", color=C["ink"], clip_on=False)
    if subtitle:
        ax.text(w / 2, h + 0.18, subtitle, ha="center", va="center",
                fontsize=9.5, color=C["muted"], clip_on=False)
    return fig, ax


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white", pad_inches=0.15)
    plt.close(fig)
    print("  ->", os.path.relpath(path, ROOT))


def box(ax, x, y, w, h, text, fc=C["blue_f"], ec=C["blue_e"],
        fs=9.5, bold=False, lw=1.4, rounded=False, align="center"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, linewidth=lw))
    tx = x + w / 2 if align == "center" else x + 0.16
    ha = "center" if align == "center" else "left"
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=C["ink"],
            linespacing=1.45)
    return (x, y, w, h)


def diamond(ax, cx, cy, w, h, text, fc=C["amber_f"], ec=C["amber_e"], fs=9):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=1.4))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            fontweight="bold", color=C["ink"])


def ellipse(ax, cx, cy, w, h, text, fs=8.2, bold=False, ec=C["gray_e"]):
    ax.add_patch(Ellipse((cx, cy), w, h, facecolor=C["white"],
                         edgecolor=ec, linewidth=1.2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=C["ink"])
    if bold:  # 主码属性：加下划线（课本图 8.1「主属性用下画线标出」）
        half = min(w / 2 - 0.08, len(text) * 0.085 + 0.12)
        ax.plot([cx - half, cx + half], [cy - h / 2 + 0.12, cy - h / 2 + 0.12],
                color=C["ink"], linewidth=1.1)


def line(ax, x1, y1, x2, y2, color=C["line"], lw=1.3, ls="-", arrow=False, z=1):
    if arrow:
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=11, color=color,
                                     linewidth=lw, linestyle=ls, zorder=z,
                                     shrinkA=0, shrinkB=0))
    else:
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw,
                linestyle=ls, zorder=z, solid_capstyle="round")


def polyline(ax, pts, color=C["line"], lw=1.3, arrow=False, ls="-"):
    for i in range(len(pts) - 1):
        last = (i == len(pts) - 2)
        line(ax, *pts[i], *pts[i + 1], color=color, lw=lw, ls=ls,
             arrow=arrow and last)


def txt(ax, x, y, s, fs=9, color=None, ha="center", va="center",
        bold=False, bbox=None, style="normal"):
    kw = dict(facecolor="white", edgecolor="none", pad=1.2) if bbox else {}
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs,
            color=color or C["muted"], fontweight="bold" if bold else "normal",
            bbox=kw if bbox else None, style=style, zorder=6)


def legend(ax, x, y, items):
    """items: [(符号说明, 颜色), ...]"""
    for i, (label, color) in enumerate(items):
        yy = y - i * 0.48
        ax.plot([x, x + 0.55], [yy, yy], color=color, linewidth=2.2)
        txt(ax, x + 0.75, yy, label, fs=8.6, ha="left", color=C["ink"])


# ================================================================ 图 1 模块结构图
def draw_module_structure():
    W, H = 20, 13
    fig, ax = canvas(W, H, "图 2-1  便民服务平台模块结构图",
                     "按高内聚、低耦合分解；箭头表示调用/依赖方向")
    # 分层背景带
    bands = [(10.2, 2.0, "表现层（蓝图 + 表单 + 模板）", C["blue_f"], C["blue_e"]),
             (6.3, 3.2, "业务层（纯函数规则 / 应用服务）", C["green_f"], C["green_e"]),
             (2.2, 3.2, "数据层（Repository + ORM 模型）", C["purple_f"], C["purple_e"])]
    for y, h, name, fc, ec in bands:
        ax.add_patch(Rectangle((0.5, y), 15.0, h, facecolor=fc,
                               edgecolor=ec, linewidth=1.0, alpha=0.55, linestyle="--"))
        txt(ax, 0.75, y + h - 0.28, name, fs=9, ha="left", bold=True, color=ec)

    box(ax, 6.0, 11.35, 4.0, 0.72, "便民服务平台（系统顶层）",
        fc="#dbeafe", ec=C["blue_e"], fs=10.5, bold=True)

    # 表现层 6 模块
    mods = [(0.9, 10.45, "用户管理\nauth"), (3.35, 10.45, "服务查询\nservices"),
            (5.8, 10.45, "在线预约\nappointments"), (8.25, 10.45, "公告资讯\nannouncements"),
            (10.7, 10.45, "反馈评价\nfeedback"), (13.15, 10.45, "后台管理\nadmin")]
    for i, (x, y, name) in enumerate(mods):
        box(ax, x, y, 2.2, 0.92, name, fc=C["white"], ec=C["blue_e"], fs=8.6)
        line(ax, 8.0, 11.35, x + 1.1, y + 0.92, color=C["blue_e"], lw=1.0)

    # 业务层
    biz = [(0.9, 7.0, "appointment_rules\n预约规则"), (3.9, 7.0, "password_policy\n密码策略"),
           (6.9, 7.0, "service_catalog\n服务检索"), (9.9, 7.0, "feedback_service\n评价服务"),
           (12.9, 7.0, "appointment_service\n预约编排")]
    for x, y, name in biz:
        box(ax, x, y, 2.7, 1.0, name, fc=C["white"], ec=C["green_e"], fs=8.4)
    # 数据层
    repo = [(0.9, 2.7, "user_repository"), (3.9, 2.7, "service_repository"),
            (6.9, 2.7, "appointment_repository"), (9.9, 2.7, "announcement_repository"),
            (12.9, 2.7, "feedback_repository")]
    for x, y, name in repo:
        box(ax, x, y, 2.7, 0.92, name, fc=C["white"], ec=C["purple_e"], fs=8.2)
    box(ax, 5.0, 4.15, 6.0, 0.85, "models / ORM（User · ServiceItem · Appointment · Announcement · Feedback）",
        fc=C["white"], ec=C["purple_e"], fs=8.6)

    # 调用/依赖箭头（表现层 -> 业务层 -> 数据层）
    for i, (x, _, _) in enumerate(mods):
        bx = [2.0, 5.0, 8.0, 11.0, 14.0][min(i, 4)]
        line(ax, x + 1.1, 10.45, bx, 8.0, color=C["green_e"], lw=1.05, arrow=True)
    for x, _, _ in biz:
        line(ax, x + 1.35, 7.0, x + 1.35, 5.0, color=C["purple_e"], lw=1.05, arrow=True)
    for x, _, _ in repo:
        line(ax, x + 1.35, 2.7, 8.0, 4.15, color=C["purple_e"], lw=0.8, ls=":")

    # 支撑层：常量表（公共耦合）
    box(ax, 0.9, 0.65, 14.6, 1.05,
        "支撑层  utils.constants（表驱动常量：状态机 / 分类 / 排序 / 时段）· utils.contracts（契约断言）",
        fc=C["amber_f"], ec=C["amber_e"], fs=9.2, bold=True)
    line(ax, 8.0, 6.3, 8.0, 1.7, color=C["amber_e"], lw=1.2, ls="--")
    txt(ax, 8.15, 3.82, "公共耦合（共享常量表）", fs=8.2, ha="left", color=C["amber_e"], bbox=True)

    # 右侧耦合分析
    box(ax, 15.8, 3.0, 3.9, 8.9, "", fc=C["gray_f"], ec=C["gray_e"], lw=1.0)
    txt(ax, 17.75, 11.45, "耦合类型判定", fs=9.6, bold=True, color=C["ink"])
    notes = [
        ("表现层 → 业务层", "数据耦合：仅传参数与返回值", C["green_e"]),
        ("业务层 → 数据层", "数据耦合：经 Repository 接口", C["purple_e"]),
        ("各层 → 常量表", "公共耦合：共享全局数据表", C["amber_e"]),
        ("规则层 ← 上下文", "无控制耦合：不传控制标志", C["blue_e"]),
        ("全系统", "无内容耦合：不直接改内部数据", C["ink"]),
    ]
    for i, (a, b, col) in enumerate(notes):
        yy = 10.6 - i * 1.42
        txt(ax, 16.05, yy, a, fs=8.8, ha="left", bold=True, color=col)
        txt(ax, 16.05, yy - 0.5, b, fs=8.1, ha="left", color=C["muted"])
    txt(ax, 17.75, 3.45, "结论：整体弱耦合、强内聚", fs=8.2, bold=True, color=C["ink"])
    save(fig, "01_module_structure.png")


# ================================================================ 图 2 UML 类图
def draw_class_diagram():
    W, H = 20, 13.5
    fig, ax = canvas(W, H, "图 3-1  领域类的 UML 类图",
                     "三层矩形：类名 / 属性 / 操作；可见性 + 公用、- 私有、# 保护；接口加 interface 前缀")
    classes = [
        (0.8, 9.5, 5.6, 3.1, "User",
         "+id: int\n+username: str\n-password_hash: str\n+email: str  +phone: str\n+role: str  +is_active: bool",
         "+set_password(raw)\n+check_password(raw): bool\n+is_admin(): bool"),
        (13.6, 9.5, 5.6, 3.1, "ServiceItem",
         "+id: int\n+name: str  +name_pinyin: str\n+category: str  +price: Decimal\n+duration_minutes: int\n+daily_capacity: int  +status: str",
         "+is_online(): bool\n+average_rating(): float"),
        (0.8, 5.4, 5.6, 3.1, "Appointment",
         "+id: int\n+user_id: int  +service_id: int\n+appointment_date: date\n+time_slot: str  +status: str\n+contact_name: str  +remark: str",
         "+change_status(new)\n+is_cancelled(): bool"),
        (13.6, 5.4, 5.6, 3.1, "Announcement",
         "+id: int\n+title: str  +content: str\n+author_id: int\n+is_published: bool\n+created_at: datetime",
         "+summary(): str"),
        (7.2, 1.0, 5.6, 3.1, "Feedback",
         "+id: int\n+user_id: int  +service_id: int\n+appointment_id: int\n+rating: int  +content: str\n+created_at: datetime",
         "+rating_text(): str"),
    ]
    for x, y, w, h, name, attrs, ops in classes:
        ah = h * 0.56
        oh = h * 0.26
        box(ax, x, y, w, h, "", fc=C["white"], ec=C["blue_e"], lw=1.5)
        # 类名区
        ax.add_patch(Rectangle((x, y + h - 0.62), w, 0.62,
                               facecolor=C["blue_f"], edgecolor=C["blue_e"], linewidth=1.2))
        txt(ax, x + w / 2, y + h - 0.31, name, fs=11, bold=True, color=C["ink"])
        line(ax, x, y + h - 0.62, x + w, y + h - 0.62, color=C["blue_e"], lw=1.2)
        line(ax, x, y + oh, x + w, y + oh, color=C["blue_e"], lw=1.2)
        txt(ax, x + 0.18, y + oh + ah / 2, attrs, fs=8.4, ha="left", color=C["ink"])
        txt(ax, x + 0.18, y + oh / 2, ops, fs=8.4, ha="left", color=C["ink"])

    # 接口示意（课本：接口名加前缀 interface）
    box(ax, 7.2, 12.35, 5.6, 0.72, "«interface» UserMixin",
        fc=C["green_f"], ec=C["green_e"], fs=9.6, bold=True)
    txt(ax, 10.0, 11.85, "↑ User 泛化（空心三角形，子类指向父类）", fs=8.6, color=C["green_e"])

    # 图例
    box(ax, 0.8, 0.15, 18.4, 0.62, "", fc=C["gray_f"], ec=C["gray_e"], lw=0.8)
    txt(ax, 10.0, 0.46,
        "符号约定：+ 公用   - 私有   # 保护    属性/操作用签名表示    具体类正常书写、抽象类加 abstract 或斜体",
        fs=8.8, color=C["ink"])
    save(fig, "02_class_diagram.png")


# ================================================================ 图 3 类关系图
def draw_class_relations():
    W, H = 20, 13
    fig, ax = canvas(W, H, "图 3-2  领域类关系图",
                     "关联用实线并标注角色名与数目；泛化＝空心三角形；聚合＝空心菱形；组合＝实心菱形")
    nodes = {
        "UserMixin": (8.1, 11.45, 3.8, 0.8),
        "User": (1.0, 8.2, 3.2, 0.9),
        "ServiceItem": (15.8, 8.2, 3.2, 0.9),
        "Appointment": (1.0, 4.3, 3.2, 0.9),
        "Announcement": (15.8, 4.3, 3.2, 0.9),
        "Feedback": (8.1, 0.9, 3.2, 0.9),
    }
    for name, (x, y, w, h) in nodes.items():
        fc = C["green_f"] if name == "UserMixin" else C["blue_f"]
        ec = C["green_e"] if name == "UserMixin" else C["blue_e"]
        box(ax, x, y, w, h, name if name != "UserMixin" else "interface UserMixin",
            fc=fc, ec=ec, fs=10, bold=True)

    def center(k, side="c"):
        x, y, w, h = nodes[k]
        return {"c": (x + w / 2, y + h / 2), "t": (x + w / 2, y + h),
                "b": (x + w / 2, y), "l": (x, y + h / 2), "r": (x + w, y + h / 2)}[side]

    # 1 泛化：User -> UserMixin（空心三角在父类端）
    x1, y1 = center("User", "t")
    x2, y2 = center("UserMixin", "b")
    line(ax, x1, y1, x2, y2 - 0.22, color=C["green_e"], lw=1.5)
    ax.add_patch(Polygon([(x2, y2), (x2 - 0.22, y2 - 0.34), (x2 + 0.22, y2 - 0.34)],
                         closed=True, facecolor=C["white"], edgecolor=C["green_e"], linewidth=1.5))
    txt(ax, 5.0, 10.2, "泛化（继承）", fs=8.6, color=C["green_e"], bbox=True)

    # 2 组合：User ◆-- Appointment
    x1, y1 = center("User", "b")
    x2, y2 = center("Appointment", "t")
    line(ax, x1, y1 - 0.22, x2, y2 + 0.02, color=C["blue_e"], lw=1.5)
    ax.add_patch(Polygon([(x1, y1), (x1 - 0.2, y1 - 0.22), (x1, y1 - 0.44), (x1 + 0.2, y1 - 0.22)],
                         closed=True, facecolor=C["blue_e"], edgecolor=C["blue_e"], linewidth=1.2))
    txt(ax, 2.6, 6.65, "组合  1", fs=8.6, color=C["blue_e"], bbox=True)
    txt(ax, 2.6, 5.6, "0..*  发起", fs=8.6, color=C["blue_e"], bbox=True)

    # 3 关联：ServiceItem -- Appointment（折线避开类框）
    a = center("ServiceItem", "b")
    b = center("Appointment", "r")
    polyline(ax, [a, (a[0], 7.2), (b[0] + 0.9, 7.2), (b[0] + 0.9, b[1]), b],
             color=C["muted"], lw=1.3)
    txt(ax, 10.0, 7.42, "关联 1 : 0..*（被预约）", fs=8.5, color=C["muted"], bbox=True)

    # 4 聚合：User ○-- Announcement（空心菱形在整体 User 端）
    a = center("User", "r")
    b = center("Announcement", "l")
    polyline(ax, [a, (a[0] + 1.0, a[1]), (a[0] + 1.0, 2.6), (b[0] - 0.6, 2.6),
                  (b[0] - 0.6, b[1]), b], color=C["amber_e"], lw=1.4)
    ax.add_patch(Polygon([(a[0], a[1]), (a[0] + 0.22, a[1] + 0.2),
                          (a[0] + 0.44, a[1]), (a[0] + 0.22, a[1] - 0.2)],
                         closed=True, facecolor=C["white"], edgecolor=C["amber_e"], linewidth=1.4))
    txt(ax, 9.0, 2.85, "聚合 1 : 0..*（发布，部分可独立存在）", fs=8.5,
        color=C["amber_e"], bbox=True)

    # 5 组合：User ◆-- Feedback（起点偏左，避免与 User—Appointment 的菱形重叠）
    a = (1.9, 8.2)
    b = center("Feedback", "l")
    polyline(ax, [a, (a[0], a[1] - 0.6), (7.0, 3.9), (7.0, b[1]), b],
             color=C["blue_e"], lw=1.3)
    ax.add_patch(Polygon([(a[0], a[1]), (a[0] + 0.18, a[1] - 0.2),
                          (a[0], a[1] - 0.4), (a[0] - 0.18, a[1] - 0.2)],
                         closed=True, facecolor=C["blue_e"], edgecolor=C["blue_e"], linewidth=1.2))
    txt(ax, 5.0, 3.68, "组合 1 : 0..*（提交）", fs=8.4, color=C["blue_e"], bbox=True)

    # 6 关联：ServiceItem -- Feedback
    a = center("ServiceItem", "b")
    b = center("Feedback", "r")
    polyline(ax, [a, (a[0] - 0.6, a[1] - 0.5), (13.0, 3.9), (13.0, b[1]), b],
             color=C["muted"], lw=1.3)
    txt(ax, 14.0, 3.68, "关联 1 : 0..*（被评价）", fs=8.4, color=C["muted"], bbox=True)

    # 7 组合/一对一：Appointment ◆-- Feedback
    a = center("Appointment", "b")
    b = center("Feedback", "l")
    polyline(ax, [a, (a[0], 2.2), (b[0] - 0.3, 2.2), (b[0] - 0.3, b[1]), b],
             color=C["purple_e"], lw=1.5)
    ax.add_patch(Polygon([(a[0], a[1]), (a[0] - 0.2, a[1] - 0.22),
                          (a[0], a[1] - 0.44), (a[0] + 0.2, a[1] - 0.22)],
                         closed=True, facecolor=C["purple_e"], edgecolor=C["purple_e"], linewidth=1.2))
    txt(ax, 4.6, 2.0, "组合 1 : 0..1（产生，一预约至多一评价）", fs=8.4,
        color=C["purple_e"], bbox=True)

    # 图例
    box(ax, 0.7, 12.15, 5.6, 0.62, "", fc=C["gray_f"], ec=C["gray_e"], lw=0.8)
    txt(ax, 3.5, 12.46, "实心菱形＝组合   空心菱形＝聚合   空心三角＝泛化   实线＝关联",
        fs=8.2, color=C["ink"])
    save(fig, "03_class_relations.png")


# ================================================================ 图 4 E-R 图
def draw_er_diagram():
    W, H = 20, 13.5
    fig, ax = canvas(W, H, "图 3-4  数据库概念结构设计 E-R 图",
                     "实体型用矩形、属性用椭圆、联系用菱形；无向边旁标注 1:1 / 1:n / m:n")
    # 实体（矩形）
    ents = {
        "users": (1.0, 10.3, 2.6, 0.85, "用户"),
        "services": (16.4, 10.3, 2.6, 0.85, "服务项目"),
        "appointments": (8.7, 6.2, 2.6, 0.85, "预约记录"),
        "announcements": (1.0, 2.3, 2.6, 0.85, "公告"),
        "feedbacks": (16.4, 2.3, 2.6, 0.85, "评价"),
    }
    for k, (x, y, w, h, name) in ents.items():
        box(ax, x, y, w, h, name, fc=C["blue_f"], ec=C["blue_e"], fs=10.5, bold=True)

    def ec_(k, side="c"):
        x, y, w, h, _ = ents[k]
        return {"c": (x + w / 2, y + h / 2), "t": (x + w / 2, y + h),
                "b": (x + w / 2, y), "l": (x, y + h / 2), "r": (x + w, y + h / 2)}[side]

    # 属性（椭圆，主码加粗+下划线）
    # 属性（椭圆）：每个实体给出主码与一个代表属性，其余属性在图 3-4 与报告表结构中完整列出
    attrs = {
        "users": [(1.4, 11.9, "用户ID", True), (3.7, 12.0, "用户名", False)],
        "services": [(15.7, 11.9, "服务ID", True), (18.4, 12.0, "服务名", False)],
        "appointments": [(7.6, 8.2, "预约ID", True), (11.9, 8.2, "状态", False)],
        "announcements": [(1.4, 1.3, "公告ID", True), (3.7, 1.3, "标题", False)],
        "feedbacks": [(15.7, 1.3, "评价ID", True), (18.4, 1.3, "星级", False)],
    }
    for k, items in attrs.items():
        for cx, cy, name, pk in items:
            ellipse(ax, cx, cy, 1.75 if len(name) > 3 else 1.5, 0.62, name,
                    fs=8, bold=pk, ec=C["blue_e"] if pk else C["gray_e"])
            ex, ey = ec_(k)
            line(ax, cx, cy, ex, ey, color=C["gray_e"], lw=0.9)

    # 联系（菱形）+ 无向边 + 联系类型
    links = [
        ("发起", 4.6, 8.7, "users", "appointments", "1", "n"),
        ("被预约", 14.3, 8.7, "services", "appointments", "1", "n"),
        ("发布", 1.9, 6.2, "users", "announcements", "1", "n"),
        ("被评价", 17.7, 6.2, "services", "feedbacks", "1", "n"),
        ("提交", 5.4, 3.6, "users", "feedbacks", "1", "n"),
        ("产生", 13.6, 3.6, "appointments", "feedbacks", "1", "1"),
    ]
    for name, cx, cy, a, b, ca, cb in links:
        diamond(ax, cx, cy, 1.9, 0.95, name, fs=9)
        ax_, ay_ = ec_(a, "c")
        bx_, by_ = ec_(b, "c")
        line(ax, ax_, ay_, cx, cy, color=C["line"], lw=1.2)
        line(ax, cx, cy, bx_, by_, color=C["line"], lw=1.2)
        # 在两端标注联系类型（按课本「无向边旁标记联系的类型」），靠近菱形以免压住属性椭圆
        mx1, my1 = ax_ + (cx - ax_) * 0.32, ay_ + (cy - ay_) * 0.32
        mx2, my2 = cx + (bx_ - cx) * 0.32, cy + (by_ - cy) * 0.32
        txt(ax, mx1, my1 + 0.22, ca, fs=9, bold=True, color=C["ink"], bbox=True)
        txt(ax, mx2, my2 + 0.22, cb, fs=9, bold=True, color=C["ink"], bbox=True)

    # 图例
    box(ax, 6.3, 12.35, 7.4, 0.72, "", fc=C["gray_f"], ec=C["gray_e"], lw=0.8)
    txt(ax, 10.0, 12.71,
        "矩形＝实体型   椭圆＝属性（加粗带下划线者为主码）   菱形＝联系   1 / n / m＝联系类型",
        fs=8.4, color=C["ink"])
    txt(ax, 10.0, 0.35,
        "每个实体仅画出主码与一个代表属性，完整属性见「图 3-5 关系模式」与报告中的表结构清单；",
        fs=8.3, color=C["muted"])
    txt(ax, 10.0, 0.02,
        "本系统实体间只有 1:1 与 1:n 联系，无 m:n 联系，故 E-R 图向关系模式转换时无需引入独立联系表。",
        fs=8.3, color=C["muted"])
    save(fig, "04_er_diagram.png")


# ================================================================ 图 5 关系图 / 关系模式
def draw_relation_schema():
    W, H = 20, 13.5
    fig, ax = canvas(W, H, "图 3-5  逻辑结构设计：关系模式与关系图",
                     "矩形＝关系，矩形内列属性，主属性加下划线；箭头＝外码 → 被参照关系的主码")
    rels = {
        "users": (1.0, 9.4, 4.4, 2.35, "users", ["id", "username", "password_hash", "email", "role"]),
        "services": (14.6, 9.4, 4.4, 2.35, "services", ["id", "name", "category", "price", "daily_capacity"]),
        "appointments": (1.0, 5.3, 4.4, 2.9, "appointments",
                         ["id", "user_id", "service_id", "appointment_date", "time_slot", "status"]),
        "announcements": (14.6, 5.3, 4.4, 2.35, "announcements",
                          ["id", "title", "content", "author_id"]),
        "feedbacks": (7.8, 1.2, 4.4, 2.9, "feedbacks",
                      ["id", "user_id", "service_id", "appointment_id", "rating", "content"]),
    }
    fk_rows = {  # 关系 -> {属性: 被参照关系}
        "appointments": {"user_id": "users", "service_id": "services"},
        "announcements": {"author_id": "users"},
        "feedbacks": {"user_id": "users", "service_id": "services", "appointment_id": "appointments"},
    }
    for k, (x, y, w, h, name, fields) in rels.items():
        box(ax, x, y, w, h, "", fc=C["white"], ec=C["blue_e"], lw=1.5)
        txt(ax, x + w / 2, y + h + 0.24, name, fs=10.5, bold=True, color=C["blue_e"])
        step = (h - 0.35) / len(fields)
        for i, f in enumerate(fields):
            fy = y + h - 0.32 - i * step
            pk = (f == "id")
            txt(ax, x + 0.22, fy, f, fs=8.8, ha="left", bold=pk, color=C["ink"])
            if pk:
                ax.plot([x + 0.2, x + 0.2 + len(f) * 0.105],
                        [fy - 0.14, fy - 0.14], color=C["ink"], linewidth=1.1)
            if k in fk_rows and f in fk_rows[k]:
                txt(ax, x + w - 0.22, fy, "FK", fs=7.6, ha="right", color=C["amber_e"], bold=True)

    # 外码箭头：从 FK 属性右侧指向被参照关系的主码
    field_y = {}
    for k, (x, y, w, h, name, fields) in rels.items():
        step = (h - 0.35) / len(fields)
        for i, f in enumerate(fields):
            field_y[(k, f)] = (x + w, y + h - 0.32 - i * step, x, y + h - 0.32 - i * step)
    arrows = [
        ("appointments", "user_id", "users", "id"),
        ("appointments", "service_id", "services", "id"),
        ("announcements", "author_id", "users", "id"),
        ("feedbacks", "user_id", "users", "id"),
        ("feedbacks", "service_id", "services", "id"),
        ("feedbacks", "appointment_id", "appointments", "id"),
    ]
    for sk, sf, tk, tf in arrows:
        sx, sy, sx_left, _ = field_y[(sk, sf)]
        _, ty, tx_left, _ = field_y[(tk, tf)]
        # 从 FK 属性文字处 指向 被参照关系的主码属性（带弧度，避免直线穿过其它关系框）
        ax.add_patch(FancyArrowPatch((sx_left + 0.12, sy), (tx_left + 0.12, ty),
                                     arrowstyle="-|>", mutation_scale=10,
                                     color=C["amber_e"], linewidth=0.95,
                                     linestyle="--", connectionstyle="arc3,rad=0.13",
                                     shrinkA=2, shrinkB=2, zorder=1))

    # 下方：关系模式 R(U)（课本 8.1.2 形式化表述，主码下划线）+ 三类完整性约束
    box(ax, 0.7, 0.05, 18.6, 1.02, "", fc=C["gray_f"], ec=C["gray_e"], lw=0.8)
    txt(ax, 10.0, 0.76,
        "关系模式 R(U)（主码加下划线）：users(id, username, …)   services(id, name, …)   appointments(id, user_id, service_id, …)",
        fs=8.0, color=C["ink"])
    txt(ax, 10.0, 0.36,
        "announcements(id, author_id, …)   feedbacks(id, appointment_id, …)   三类完整性约束：实体（主码非空唯一）/ 参照（外码有效）/ 用户自定义（CHECK）",
        fs=8.0, color=C["ink"])
    save(fig, "05_relation_schema.png")


# ================================================================ 图 6 数据库设计 6 阶段
def draw_db_process():
    W, H = 20, 9
    fig, ax = canvas(W, H, "图 3-3  数据库设计的六个阶段",
                     "数据库构造按六阶段推进，每阶段均有对应产物")
    stages = [
        ("① 需求分析", "明确用户组成与数据需求\n六大模块的数据字典", C["blue_f"], C["blue_e"]),
        ("② 概念结构设计", "抽象为信息结构\n输出 E-R 图（图 3-4）", C["amber_f"], C["amber_e"]),
        ("③ 逻辑结构设计", "E-R 图 → 关系模式\n三范式 + 三类完整性约束", C["green_f"], C["green_e"]),
        ("④ 物理结构设计", "索引 / 存储 / CHECK\n复合索引 ix_appt_slot", C["purple_f"], C["purple_e"]),
        ("⑤ 数据库实施", "ORM 模型 + DDL\ndocs/schema.sql", C["blue_f"], C["blue_e"]),
        ("⑥ 运行与维护", "迁移脚本 / 数据回填\n测试环境隔离", C["gray_f"], C["gray_e"]),
    ]
    x = 0.6
    for i, (name, detail, fc, ec) in enumerate(stages):
        box(ax, x, 3.2, 2.9, 2.2, name, fc=fc, ec=ec, fs=9.6, bold=True)
        txt(ax, x + 1.45, 2.55, detail, fs=8.1, color=C["ink"], ha="center")
        if i < len(stages) - 1:
            line(ax, x + 2.9, 4.3, x + 3.22, 4.3, color=C["line"], lw=1.6, arrow=True)
        x += 3.22
    # 反馈回路（课本：评价设计、性能预测，未达标则返回修改）
    polyline(ax, [(19.0, 3.2), (19.0, 1.55), (0.6, 1.55), (0.6, 3.2)],
             color=C["muted"], lw=1.0, ls="--", arrow=True)
    txt(ax, 10.0, 1.3, "未达到设计要求则回溯调整（评价设计、性能预测 → 返回修改物理/逻辑结构）",
        fs=8.5, color=C["muted"])
    box(ax, 0.6, 6.0, 18.8, 1.15, "", fc=C["gray_f"], ec=C["gray_e"], lw=0.8)
    txt(ax, 10.0, 6.58,
        "E-R 图 → 关系模式转换三规则：1:1 可独立或合并；1:n 可独立或并入 n 端；m:n 必须转为独立关系模式",
        fs=9, color=C["ink"], bold=True)
    save(fig, "06_db_design_process.png")


# ================================================================ 图 7 页面结构设计图
def draw_page_structure():
    W, H = 20, 13.5
    fig, ax = canvas(W, H, "图 4-1  页面结构设计图",
                     "左侧：Jinja2 模板继承层级；右侧：按角色划分的页面跳转逻辑（写操作采用 POST-Redirect-GET）")
    # 左：模板继承
    box(ax, 0.6, 11.6, 8.6, 0.9, "base.html（父模板：导航 + flash 反馈区 + 页脚）",
        fc=C["blue_f"], ec=C["blue_e"], fs=9.2, bold=True)
    children = [
        (0.6, 10.2, "main/index.html 首页"),
        (0.6, 9.25, "services/list.html 服务查询"),
        (0.6, 8.3, "services/detail.html 服务详情"),
        (0.6, 7.35, "appointments/create.html 在线预约"),
        (0.6, 6.4, "appointments/mine.html 我的预约"),
        (0.6, 5.45, "auth/register · login · profile"),
        (0.6, 4.5, "announcements/list · detail"),
        (0.6, 3.55, "feedback/create · mine"),
        (0.6, 2.6, "admin/dashboard · services · users · appointments · feedbacks"),
        (0.6, 1.65, "errors/403 · 404 · 500"),
    ]
    for x, y, name in children:
        box(ax, x + 0.5, y, 7.9, 0.62, name, fc=C["white"], ec=C["blue_e"], fs=8.5, align="left")
        line(ax, 1.3, y + 0.62, 1.3, y + 0.86, color=C["blue_e"], lw=0.9)
    line(ax, 1.3, 11.6, 1.3, 2.27, color=C["blue_e"], lw=1.0, ls=":")
    txt(ax, 4.9, 0.75, "模板继承：子模板只覆盖 content 块，导航与反馈保持一致",
        fs=8.4, color=C["muted"])

    # 右：角色跳转泳道
    lanes = [
        (11.0, "游客", C["gray_f"], C["gray_e"],
         ["首页", "→ 服务查询", "→ 服务详情", "→（引导注册/登录）"]),
        (8.8, "普通用户", C["green_f"], C["green_e"],
         ["登录 → 服务查询", "→ 服务详情 → 在线预约", "→ 我的预约（取消）", "→ 已完成 → 提交评价"]),
        (5.6, "管理员", C["amber_f"], C["amber_e"],
         ["登录 → 后台管理（默认落地）", "→ 预约管理（自动办结）", "→ 服务管理 / 用户管理", "→ 评价查看（只读）"]),
    ]
    for y, name, fc, ec, steps in lanes:
        box(ax, 10.0, y, 9.4, 1.85, "", fc=fc, ec=ec, lw=1.0)
        txt(ax, 10.35, y + 1.55, name, fs=9.4, bold=True, color=ec, ha="left")
        for i, s in enumerate(steps):
            txt(ax, 10.35, y + 1.15 - i * 0.33, s, fs=8.2, ha="left", color=C["ink"])
    # 跨角色跳转箭头
    line(ax, 14.7, 8.8, 14.7, 10.6, color=C["muted"], lw=1.2, arrow=True, ls="--")
    txt(ax, 15.0, 9.7, "注册/登录", fs=8, ha="left", color=C["muted"], bbox=True)
    line(ax, 14.7, 7.45, 14.7, 8.8, color=C["muted"], lw=1.2, arrow=True, ls="--")
    txt(ax, 15.0, 8.1, "角色切换", fs=8, ha="left", color=C["muted"], bbox=True)
    # PRG 说明
    box(ax, 10.0, 3.4, 9.4, 1.5, "", fc=C["purple_f"], ec=C["purple_e"], lw=1.0)
    txt(ax, 10.35, 4.55, "写操作反馈机制（可反馈性与容错性）", fs=9.2,
        bold=True, color=C["purple_e"], ha="left")
    txt(ax, 10.35, 4.05, "POST 成功 → 302 重定向 → GET 结果页（PRG），避免刷新重复提交",
        fs=8.3, ha="left", color=C["ink"])
    txt(ax, 10.35, 3.75, "失败 → 原页保留输入 + 逐字段红字提示；flash 显示成功/失败/警告",
        fs=8.3, ha="left", color=C["ink"])
    save(fig, "07_page_structure.png")


# ================================================================ 图 8 程序控制流图
def draw_control_flow():
    W, H = 20, 12
    fig, ax = canvas(W, H, "图 2-1  被测单元 cancel_appointment 的程序控制流图",
                     "N=9 个结点，E=11 条边，判定结点 3 个；V(G)=E−N+2=11−9+2=4，V(G)=P+1=3+1=4，区域数=4")
    # 结点坐标
    pos = {
        1: (3.0, 9.6), 2: (3.0, 8.3), 3: (3.0, 6.9),
        4: (6.2, 5.5), 5: (6.2, 3.9),
        6: (0.9, 5.5), 7: (4.2, 2.3), 8: (8.4, 2.3), 9: (6.2, 0.9),
    }
    edges = [(1, 2, ""), (2, 3, ""), (3, 6, "F 记录不存在"), (3, 4, "T"),
             (4, 7, "F 非本人"), (4, 5, "T"), (5, 8, "F 状态不可取消"),
             (5, 9, "T 取消成功"), (6, 9, ""), (7, 9, ""), (8, 9, "")]
    for a, b, lab in edges:
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        # 用带弧度的连线避免重叠
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=12, color=C["line"], linewidth=1.4,
                                     connectionstyle="arc3,rad=0.06", shrinkA=13, shrinkB=13))
        if lab:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            txt(ax, mx + 0.55, my + 0.22, lab, fs=8.1, color=C["amber_e"], bbox=True)
    # 结点
    for n, (x, y) in pos.items():
        is_pred = n in (3, 4, 5)
        ax.add_patch(Circle((x, y), 0.34, facecolor=C["amber_f"] if is_pred else C["blue_f"],
                            edgecolor=C["amber_e"] if is_pred else C["blue_e"], linewidth=1.6, zorder=4))
        txt(ax, x, y, str(n), fs=10, bold=True, color=C["ink"])
        labels = {1: "入口", 2: "查询预约记录", 3: "记录存在?", 4: "是本人/管理员?",
                  5: "状态可取消?", 6: "返回(不存在)", 7: "返回(越权)",
                  8: "返回(终态)", 9: "返回(取消成功) / 出口"}
        if n in (1, 2, 3):
            lx, ly = x, y + 0.62
        elif n in (4, 5):
            lx, ly = x + 1.25, y
        elif n == 6:
            lx, ly = x - 0.45, y - 0.62
        else:
            lx, ly = x, y - 0.62
        txt(ax, lx, ly, labels[n], fs=8.2, color=C["muted"], bbox=True)

    # 4 条独立路径
    box(ax, 11.0, 2.0, 8.4, 8.0, "", fc=C["gray_f"], ec=C["gray_e"], lw=1.0)
    txt(ax, 15.2, 9.55, "由 V(G)=4 导出的 4 条独立路径", fs=9.8, bold=True, color=C["ink"])
    paths = [
        ("P1  1-2-3-6-9", "记录不存在 → 返回 False", C["blue_e"]),
        ("P2  1-2-3-4-7-9", "非本人且非管理员 → 返回 False", C["green_e"]),
        ("P3  1-2-3-4-5-8-9", "状态为终态 → 返回 False", C["amber_e"]),
        ("P4  1-2-3-4-5-9", "校验通过 → 置 cancelled 并返回 True", C["purple_e"]),
    ]
    for i, (p, d, col) in enumerate(paths):
        yy = 8.7 - i * 1.35
        txt(ax, 11.35, yy, p, fs=9.2, ha="left", bold=True, color=col)
        txt(ax, 11.35, yy - 0.48, d, fs=8.4, ha="left", color=C["ink"])
    txt(ax, 15.2, 2.4, "每条路径至少引入一条新边，达到基本路径覆盖", fs=8.4, color=C["muted"])
    # 判定结点说明
    txt(ax, 3.0, 11.0, "黄色结点＝判定结点（3 个）    蓝色结点＝顺序/出口结点", fs=8.6, color=C["muted"])
    save(fig, "08_control_flow.png")


# ================================================================ 图 9 因果图
def draw_cause_effect_graph():
    W, H = 20, 13
    fig, ax = canvas(W, H, "图 1-1  在线预约提交的因果图",
                     "左为原因 C1~C8，右为结果 E1~E7；∧ 与、¬ 非、∨ 或；底部标注 R / M / E 约束")
    causes = ["C1 服务已上架", "C2 已选预约日期", "C3 日期在 30 天窗口内",
              "C4 时段合法", "C5 姓名≥2 字", "C6 手机号合法",
              "C7 无重复预约", "C8 名额未满"]
    results = ["E1 预约创建成功", "E2 服务已下架", "E3 请选择预约日期",
               "E4 日期非法/超窗口", "E5 时段无效", "E6 姓名/手机号错误",
               "E7 重复预约/名额已满"]
    cy0, cstep = 10.9, 1.22
    for i, c in enumerate(causes):
        y = cy0 - i * cstep
        ellipse(ax, 2.6, y, 3.9, 0.78, c, fs=8.6, ec=C["blue_e"])
        line(ax, 4.55, y, 6.2, y, color=C["blue_e"], lw=0.9)
    ry0, rstep = 10.6, 1.42
    for i, r in enumerate(results):
        y = ry0 - i * rstep
        ellipse(ax, 17.4, y, 4.0, 0.8, r, fs=8.6, ec=C["green_e"])
        line(ax, 15.4, y, 13.4, y, color=C["green_e"], lw=0.9)

    # 原因汇流线
    line(ax, 6.2, 1.1, 6.2, 11.3, color=C["blue_e"], lw=1.1, ls="--")
    # 三个逻辑门
    gates = [(8.0, 5.6, "∧ 与门\n全部原因成立", C["amber_f"], C["amber_e"]),
             (8.0, 8.5, "¬ 非门\n对应原因不成立", C["purple_f"], C["purple_e"]),
             (8.0, 2.7, "∨ 或门\n任一原因不成立", C["purple_f"], C["purple_e"])]
    for gx, gy, label, fc, ec in gates:
        box(ax, gx, gy, 2.7, 1.0, label, fc=fc, ec=ec, fs=8.6, bold=True)
        line(ax, 6.2, gy + 0.5, gx, gy + 0.5, color=C["line"], lw=1.2, arrow=True)
    # 门 -> 结果
    line(ax, 10.7, 6.1, 13.4, ry0, color=C["green_e"], lw=1.6, arrow=True)
    txt(ax, 12.1, 8.4, "全部为真", fs=8.2, color=C["green_e"], bbox=True)
    for dst in (1, 2, 3, 4):
        line(ax, 10.7, 9.0, 13.4, ry0 - dst * rstep,
             color=C["purple_e"], lw=0.9, arrow=True, ls=":")
    for dst in (5, 6):
        line(ax, 10.7, 3.2, 13.4, ry0 - dst * rstep,
             color=C["purple_e"], lw=0.9, arrow=True, ls=":")
    txt(ax, 13.4, 11.65, "原因", fs=9, bold=True, color=C["blue_e"])
    txt(ax, 17.4, 11.65, "结果", fs=9, bold=True, color=C["green_e"])

    box(ax, 0.7, 0.15, 18.6, 1.35, "", fc=C["gray_f"], ec=C["gray_e"], lw=0.8)
    txt(ax, 10.0, 1.1,
        "约束：R 要求——C3 以 C2 为前提；M 屏蔽——表单字段错误时不再报告业务规则；E 互斥——E1 与各失败结果不能同时成立",
        fs=8.2, color=C["ink"])
    txt(ax, 10.0, 0.58,
        "因果图 → 判定表：8 个原因共 2^8=256 种组合，经约束剪枝保留 12 列，保证每个原因的真/假与各结果至少出现一次",
        fs=8.2, color=C["ink"])
    save(fig, "09_cause_effect_graph.png")


# ================================================================ 图 10 状态迁移图
def draw_state_transition():
    W, H = 20, 10
    fig, ax = canvas(W, H, "图 1-2  预约状态迁移图",
                     "功能图 = 状态迁移图 + 状态内局部判定表；虚线箭头为被状态机拒绝的非法迁移")
    states = {
        "pending": (1.0, 5.0, 3.5, 1.15, "待确认 pending"),
        "confirmed": (8.2, 7.0, 3.5, 1.15, "已确认 confirmed"),
        "completed": (15.5, 7.0, 3.5, 1.15, "已完成 completed（终态）"),
        "cancelled": (8.2, 2.4, 3.5, 1.15, "已取消 cancelled（终态）"),
    }
    for k, (x, y, w, h, name) in states.items():
        fc = C["green_f"] if k == "completed" else (
            C["gray_f"] if k == "cancelled" else C["blue_f"])
        ec = C["green_e"] if k == "completed" else (
            C["gray_e"] if k == "cancelled" else C["blue_e"])
        box(ax, x, y, w, h, name, fc=fc, ec=ec, fs=9.4, bold=True)

    def c(k, side="c"):
        x, y, w, h, _ = states[k]
        return {"c": (x + w / 2, y + h / 2), "t": (x + w / 2, y + h),
                "b": (x + w / 2, y), "l": (x, y + h / 2), "r": (x + w, y + h / 2)}[side]

    # 合法迁移
    line(ax, *c("pending", "r"), *c("confirmed", "l"), color=C["blue_e"], lw=1.8, arrow=True)
    txt(ax, 6.6, 6.35, "管理员受理", fs=8.6, color=C["blue_e"], bbox=True)
    line(ax, *c("confirmed", "r"), *c("completed", "l"), color=C["green_e"], lw=1.8, arrow=True)
    txt(ax, 13.5, 7.9, "时段结束自动办结 / 提前办结", fs=8.3, color=C["green_e"], bbox=True)
    polyline(ax, [c("pending", "b"), (2.75, 3.0), c("cancelled", "l")],
             color=C["muted"], lw=1.4, arrow=True)
    txt(ax, 4.4, 3.2, "用户取消 / 管理员拒绝", fs=8.2, color=C["muted"], bbox=True)
    line(ax, *c("confirmed", "b"), *c("cancelled", "t"), color=C["muted"], lw=1.4, arrow=True)
    txt(ax, 11.0, 4.6, "用户取消", fs=8.4, color=C["muted"], bbox=True)

    # 非法迁移（虚线 + 叉）
    polyline(ax, [c("pending", "t"), (2.75, 8.6), c("confirmed", "t")],
             color=C["amber_e"], lw=1.1, ls="--")
    txt(ax, 5.0, 8.85, "× pending → completed 被拒绝", fs=8.2, color=C["amber_e"], bbox=True)
    txt(ax, 17.25, 5.6, "× 终态不可再迁移\n× completed/cancelled 互转被拒",
        fs=8.2, color=C["amber_e"], bbox=True)

    # 状态内局部判定
    box(ax, 0.7, 0.2, 18.6, 1.5, "", fc=C["gray_f"], ec=C["gray_e"], lw=0.8)
    txt(ax, 10.0, 1.32, "状态内局部判定表：每个状态对「取消 / 推进 / 评价」三个事件分别给出允许或拒绝的判定",
        fs=8.3, color=C["ink"])
    txt(ax, 10.0, 0.82,
        "pending：可取消、可受理、不可评价  |  confirmed：可取消、可办结、不可评价  |  completed：不可取消、不可迁移、可评价  |  cancelled：全部拒绝",
        fs=8.2, color=C["ink"])
    save(fig, "10_state_transition.png")


def main():
    print("生成实验报告设计图（图面不标注教材章节）：")
    draw_module_structure()
    draw_class_diagram()
    draw_class_relations()
    draw_er_diagram()
    draw_relation_schema()
    draw_db_process()
    draw_page_structure()
    draw_control_flow()
    draw_cause_effect_graph()
    draw_state_transition()
    print("完成，输出目录：", OUT)


if __name__ == "__main__":
    main()
