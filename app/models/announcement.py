"""领域对象：公告（Announcement）。对应模块：公告资讯。"""
from datetime import datetime

from app.extensions import db


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
        """列表页摘要：正文前 60 字。"""
        text = (self.content or "").strip()
        return text[:60] + ("…" if len(text) > 60 else "")

    def __repr__(self):
        return f"<Announcement {self.title}>"
