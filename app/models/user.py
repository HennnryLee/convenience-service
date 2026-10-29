"""领域对象：用户（User）。

对应模块：用户管理。同时承担 Flask-Login 的认证主体（继承 UserMixin）。
"""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    """用户实体。

    属性不变量（Invariant）：
        - username 长度 3–20，全局唯一；
        - email 唯一且格式合法（由表单层校验）；
        - role ∈ {user, admin}（由数据库 CHECK 约束保证）；
        - password_hash 永不为空，明文密码不落库。
    """

    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint("role IN ('user', 'admin')", name="ck_user_role"),
        db.CheckConstraint("length(username) >= 3", name="ck_username_len"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(11))
    real_name = db.Column(db.String(30))
    role = db.Column(db.String(10), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now())

    # ---- 关联关系（一对多；删除用户时级联清理其预约与评价）----
    appointments = db.relationship(
        "Appointment", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    feedbacks = db.relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    announcements = db.relationship("Announcement", back_populates="author", lazy="dynamic")

    # ------------------------------------------------------------------ 行为
    def set_password(self, raw_password):
        """前置条件：raw_password 为非空字符串；后置条件：生成哈希，明文不保存。"""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """后置条件：返回 bool，永不抛异常。"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def role_text(self):
        return "管理员" if self.is_admin else "普通用户"

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
