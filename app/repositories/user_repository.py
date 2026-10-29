"""用户数据访问层（Repository 模式）。

职责：封装全部针对 users 表的 ORM 操作，使业务层不直接出现查询构造代码。
通用增删改查继承自 BaseRepository，本类只保留用户特有的查询。
"""
from sqlalchemy import or_, select

from app.extensions import db
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    model = User

    @staticmethod
    def get_by_username(username):
        return db.session.scalar(select(User).where(User.username == username))

    @staticmethod
    def get_by_email(email):
        return db.session.scalar(select(User).where(User.email == email))

    @staticmethod
    def get_by_login(login):
        """支持用户名或邮箱登录。"""
        if not login:
            return None
        return db.session.scalar(
            select(User).where(or_(User.username == login, User.email == login))
        )

    @staticmethod
    def username_exists(username):
        return UserRepository.get_by_username(username) is not None

    @staticmethod
    def email_exists(email):
        return UserRepository.get_by_email(email) is not None

    @classmethod
    def create(cls, username, email, password, phone=None, real_name=None, role="user"):
        """创建用户（密码在此处哈希，明文不落库）。"""
        user = User(
            username=username,
            email=email,
            phone=phone,
            real_name=real_name,
            role=role,
        )
        user.set_password(password)
        return cls.add(user)

    @classmethod
    def set_active(cls, user, active=True):
        user.is_active = bool(active)
        return cls.save(user)

    @staticmethod
    def search(keyword=None, role=None, page=1, per_page=10):
        """后台用户查询：支持关键词（用户名/姓名/邮箱）与角色过滤、分页。"""
        stmt = select(User)
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                or_(User.username.like(pattern), User.real_name.like(pattern), User.email.like(pattern))
            )
        if role:
            stmt = stmt.where(User.role == role)
        stmt = stmt.order_by(User.created_at.desc())
        return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def count(role=None):
        stmt = select(User)
        if role:
            stmt = stmt.where(User.role == role)
        return db.session.scalar(select(db.func.count()).select_from(stmt.subquery()))
