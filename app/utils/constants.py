"""系统常量与"表驱动"配置。

把状态流转、分类映射、时段列表等易变规则集中为数据表（字典/元组），
替代散落在业务代码中的 if/elif 与魔法字符串 —— 这是教材"表驱动编程"思想的落地。
"""

# ---------------- 可预约时段 ----------------
TIME_SLOTS = (
    "09:00-10:00",
    "10:00-11:00",
    "11:00-12:00",
    "14:00-15:00",
    "15:00-16:00",
    "16:00-17:00",
)

# ---------------- 服务分类映射（分类码 -> 展示名） ----------------
SERVICE_CATEGORIES = {
    "government": "政务服务",
    "life": "生活服务",
    "medical": "医疗健康",
    "education": "教育咨询",
    "repair": "维修服务",
}

# ---------------- 预约状态与状态机 ----------------
APPOINTMENT_STATUS_TEXT = {
    "pending": "待确认",
    "confirmed": "已确认",
    "completed": "已完成",
    "cancelled": "已取消",
}

# 表驱动状态机：当前状态 -> 允许迁移到的状态集合
APPOINTMENT_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"completed", "cancelled"},
    "completed": set(),   # 终态
    "cancelled": set(),   # 终态
}

# ---------------- 用户角色 ----------------
USER_ROLES = {
    "user": "普通用户",
    "admin": "管理员",
}

# ---------------- 服务查询排序方式（键 -> SQLAlchemy 排序规则标识） ----------------
SORT_OPTIONS = {
    "default": "综合排序（推荐）",
    "name": "按名称",
    "price_asc": "价格从低到高",
    "price_desc": "价格从高到低",
    "popular": "按预约热度",
}

# ---------------- 评价星级文案 ----------------
RATING_TEXT = {
    1: "很不满意",
    2: "不满意",
    3: "一般",
    4: "满意",
    5: "非常满意",
}


def status_text(status):
    """状态码 -> 中文文案（表驱动查表，避免 if/elif 链）。"""
    return APPOINTMENT_STATUS_TEXT.get(status, "未知状态")


def category_text(code):
    """分类码 -> 中文文案。"""
    return SERVICE_CATEGORIES.get(code, "其它")
