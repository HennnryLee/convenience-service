"""领域对象：服务项目（ServiceItem）。

对应模块：服务查询 / 后台管理（服务维护）。
"""
from datetime import datetime

from sqlalchemy.orm import validates

from app.extensions import db
from app.utils.pinyin import to_pinyin_key


class ServiceItem(db.Model):
    """服务项目实体。

    属性不变量：
        - name 全局唯一且非空；
        - name_pinyin 恒等于 to_pinyin_key(name)，由写入钩子自动维护；
        - category ∈ SERVICE_CATEGORIES 的键（表单层用 SelectField 收敛取值）；
        - daily_capacity > 0；
        - price >= 0；
        - status ∈ {online, offline}（由 CHECK 约束保证）。
    """

    __tablename__ = "services"
    __table_args__ = (
        db.CheckConstraint("status IN ('online', 'offline')", name="ck_service_status"),
        db.CheckConstraint("daily_capacity > 0", name="ck_service_capacity"),
        db.CheckConstraint("price >= 0", name="ck_service_price"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    # 拼音排序键：让"按名称"排出用户直觉的 A→Z，而不是 UTF-8 字节序。
    # 冗余列，由下面的 @validates 自动维护，调用方无需关心。
    name_pinyin = db.Column(db.String(255), nullable=False, default="", index=True)
    category = db.Column(db.String(20), nullable=False, default="life", index=True)
    description = db.Column(db.Text)
    address = db.Column(db.String(200))
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    daily_capacity = db.Column(db.Integer, nullable=False, default=5)  # 每个时段的容量
    status = db.Column(db.String(10), nullable=False, default="online")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now())

    appointments = db.relationship(
        "Appointment", back_populates="service", cascade="all, delete-orphan", lazy="dynamic"
    )
    feedbacks = db.relationship("Feedback", back_populates="service", lazy="dynamic")

    @validates("name")
    def _sync_name_pinyin(self, key, value):
        """名称被赋值/修改时同步排序键。

        放在实体层而不是视图层，是为了让 seed、后台新建、后台编辑、测试造数
        等所有入口都自动生效 —— 避免"某条路径漏算拼音"导致排序静默退化。

        同时在此处去掉名称首尾空白：唯一约束按去空白后的值比较，
        否则 "身份证换领办理" 与 "身份证换领办理 " 会绕过重名校验。
        """
        if isinstance(value, str):
            value = value.strip()
        self.name_pinyin = to_pinyin_key(value)
        return value

    # ------------------------------------------------------------------ 行为
    @property
    def is_online(self):
        return self.status == "online"

    @property
    def average_rating(self):
        """后置条件：无评价时返回 None（而不是 0，避免"0 分"误导）。"""
        ratings = [fb.rating for fb in self.feedbacks if fb.rating]
        if not ratings:
            return None
        return round(sum(ratings) / len(ratings), 1)

    def __repr__(self):
        return f"<ServiceItem {self.name}>"
