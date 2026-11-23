"""领域对象：公告（Announcement）。对应模块：公告资讯。"""
from datetime import datetime

from app.extensions import db
from app.utils.constants import ANNOUNCEMENT_SUMMARY_LENGTH


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(), index=True)

    author = db.relationship("User", back_populates="announcements")

    @property
    def summary(self):
        """列表页摘要：正文前 ANNOUNCEMENT_SUMMARY_LENGTH 字（常量化，避免魔法数字）。"""
        limit = ANNOUNCEMENT_SUMMARY_LENGTH
        text = (self.content or "").strip()
        return text[:limit] + ("…" if len(text) > limit else "")

    def __repr__(self):
        return f"<Announcement {self.title}>"
