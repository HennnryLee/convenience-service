"""领域模型包：集中导出，供 db.create_all 与其它层引用。

类关系概览：
    User 1───* Appointment *───1 ServiceItem
    User 1───* Feedback   *───1 ServiceItem
    Appointment 1───0..1 Feedback（组合：一条预约最多一条评价）
    User 1───* Announcement（聚合：公告可独立于作者存在）
"""
from .announcement import Announcement
from .appointment import Appointment
from .feedback import Feedback
from .service import ServiceItem
from .user import User

__all__ = ["User", "ServiceItem", "Appointment", "Announcement", "Feedback"]
