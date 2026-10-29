"""数据访问层基类（重构产物：提炼超类 Extract Superclass + 方法上移 Pull Up Method）。

重构动机：5 个 Repository 中重复出现
    db.session.add(x); db.session.commit()
    for k, v in fields.items(): setattr(...)
    db.session.get(Model, id)
等样板代码，属于典型的**重复代码**坏味道。

重构做法：把这些公共操作上移到 BaseRepository，各子 Repository 只保留差异化查询。
子类必须设置 model 属性，用于 get() 等通用操作。
"""
from app.extensions import db


class BaseRepository:
    """通用 CRUD 操作。子类通过 `model` 指定实体类型。"""

    model = None

    @classmethod
    def add(cls, entity, commit=True):
        db.session.add(entity)
        if commit:
            db.session.commit()
        return entity

    @classmethod
    def save(cls, entity=None):
        """提交当前事务（用于已跟踪实体的修改）。"""
        db.session.commit()
        return entity

    @classmethod
    def delete(cls, entity):
        db.session.delete(entity)
        db.session.commit()

    @classmethod
    def get(cls, entity_id):
        if entity_id is None:
            return None
        return db.session.get(cls.model, entity_id)

    @classmethod
    def update(cls, entity, commit=True, **fields):
        for key, value in fields.items():
            setattr(entity, key, value)
        if commit:
            db.session.commit()
        return entity

    @classmethod
    def count_all(cls):
        from sqlalchemy import func, select

        return db.session.scalar(select(func.count()).select_from(cls.model))
