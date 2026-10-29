"""公告数据访问层。"""
from sqlalchemy import select

from app.extensions import db
from app.models.announcement import Announcement


class AnnouncementRepository:
    @staticmethod
    def create(title, content, author_id=None, is_published=True):
        ann = Announcement(title=title, content=content, author_id=author_id, is_published=is_published)
        db.session.add(ann)
        db.session.commit()
        return ann

    @staticmethod
    def get(announcement_id):
        return db.session.get(Announcement, announcement_id)

    @staticmethod
    def search(keyword=None, only_published=True, page=1, per_page=10):
        stmt = select(Announcement)
        if only_published:
            stmt = stmt.where(Announcement.is_published.is_(True))
        if keyword:
            pattern = f"%{keyword}%"
            stmt = stmt.where(
                Announcement.title.like(pattern) | Announcement.content.like(pattern)
            )
        stmt = stmt.order_by(Announcement.created_at.desc())
        return db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def update(announcement, **fields):
        for key, value in fields.items():
            setattr(announcement, key, value)
        db.session.commit()
        return announcement

    @staticmethod
    def delete(announcement):
        db.session.delete(announcement)
        db.session.commit()

    @staticmethod
    def latest(limit=5):
        stmt = (
            select(Announcement)
            .where(Announcement.is_published.is_(True))
            .order_by(Announcement.created_at.desc())
            .limit(limit)
        )
        return list(db.session.scalars(stmt))
