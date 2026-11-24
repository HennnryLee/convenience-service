"""演示数据（可被 CLI、run.py 与测试复用）。

重构要点（对照《软件构造》第 6 章）：
  - 原先演示数据写在项目根目录的 seed.py，业务包无法复用；
    现下沉到 app/seed_data.py，根目录 seed.py 仅保留兼容入口；
  - 全部查询改为 SQLAlchemy 2.0 的 select() 写法，去掉遗留的 Model.query；
  - 整个灌数据过程放在一个事务里：要么全部成功，要么回滚，不留半套数据；
  - 幂等：同名用户/服务/公告已存在则跳过，绝不删除或覆盖真实数据。
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.extensions import db
from app.models import Announcement, Appointment, Feedback, ServiceItem, User

SERVICES = [
    dict(name="身份证换领办理", category="government", price=20, capacity=3,
         address="市民之家 A 区 3 号窗口",
         description="居民身份证到期换领、遗失补办、信息变更等政务服务。"),
    dict(name="社保卡申领", category="government", price=0, capacity=5,
         address="市民之家 B 区 1 号窗口",
         description="社会保障卡首次申领、补换卡及激活服务。"),
    dict(name="住房公积金提取咨询", category="government", price=0, capacity=4,
         address="市民之家 B 区 5 号窗口",
         description="租房、购房、退休等情形的公积金提取政策咨询与办理。"),
    dict(name="家庭水电维修", category="life", price=60, capacity=2,
         address="上门服务（市区范围内）",
         description="水管漏水、电路故障、开关插座更换等家庭维修服务。"),
    dict(name="管道疏通", category="life", price=80, capacity=2,
         address="上门服务（市区范围内）",
         description="厨房、卫生间下水道堵塞疏通，含基础清理。"),
    dict(name="社区洗衣干洗", category="life", price=35, capacity=6,
         address="社区便民服务点 1 楼",
         description="衣物干洗、床品清洗、皮具护理预约。"),
    dict(name="老年人健康体检预约", category="medical", price=0, capacity=4,
         address="社区卫生服务中心 2 楼",
         description="65 岁以上老年人年度免费体检预约。"),
    dict(name="儿童疫苗接种咨询", category="medical", price=0, capacity=5,
         address="社区卫生服务中心 1 楼",
         description="免疫规划疫苗接种时间、禁忌与注意事项咨询。"),
    dict(name="课后托管咨询", category="education", price=0, capacity=5,
         address="社区教育活动室",
         description="小学生课后托管、寒暑假兴趣班咨询与报名。"),
    dict(name="成人职业技能培训报名", category="education", price=300, capacity=8,
         address="社区教育学院 3 楼",
         description="电工、育婴、电商直播等职业技能培训报名。"),
    dict(name="家电上门检修", category="repair", price=50, capacity=3,
         address="上门服务（市区范围内）",
         description="空调、冰箱、洗衣机等家电故障检测与维修。"),
    dict(name="手机电脑维修", category="repair", price=40, capacity=3,
         address="便民维修点 2 楼 205",
         description="手机换屏换电池、电脑清灰系统重装等服务。"),
]

ANNOUNCEMENTS = [
    dict(title="市民之家周末延时服务通知",
         content="自本月起，市民之家周六上午 9:00-12:00 提供延时服务，可办理身份证、社保卡等高频事项。"),
    dict(title="社区水电维修服务价格调整公示",
         content="根据最新公示价格，家庭水电维修基础上门费调整为 60 元/次，材料费按实际结算。"),
    dict(title="老年人免费体检开始预约",
         content="65 岁以上老年人年度免费体检即日起开放预约，请携带身份证前往社区卫生服务中心。"),
]


def _get_user(username):
    return db.session.scalar(select(User).where(User.username == username))


def _add_user(username, email, password, **fields):
    existing = _get_user(username)
    if existing is not None:
        return existing, 0
    user = User(username=username, email=email, **fields)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user, 1


def _seed_users(created):
    """建立演示用户；返回 (admin, zhangsan)。"""
    admin, count = _add_user(
        "admin", "admin@example.com", "Admin@123", real_name="系统管理员", role="admin"
    )
    created["users"] += count
    zhangsan, count = _add_user(
        "zhangsan", "zhangsan@example.com", "User@123",
        real_name="张三", phone="13800138000", role="user",
    )
    created["users"] += count
    return admin, zhangsan


def _seed_services(created):
    """补齐演示服务；已存在同名服务则跳过。"""
    existing_names = set(db.session.scalars(select(ServiceItem.name)).all())
    for item in SERVICES:
        if item["name"] in existing_names:
            continue
        db.session.add(ServiceItem(
            name=item["name"],
            category=item["category"],
            description=item["description"],
            address=item["address"],
            price=item["price"],
            duration_minutes=30,
            daily_capacity=item["capacity"],
            status="online",
        ))
        created["services"] += 1
    db.session.flush()


def _seed_announcements(created, author_id):
    """补齐演示公告；已存在同标题公告则跳过。"""
    existing_titles = set(db.session.scalars(select(Announcement.title)).all())
    for ann in ANNOUNCEMENTS:
        if ann["title"] in existing_titles:
            continue
        db.session.add(Announcement(
            title=ann["title"],
            content=ann["content"],
            author_id=author_id,
            is_published=True,
        ))
        created["announcements"] += 1
    db.session.flush()


def _seed_appointments(created, user_id):
    """为演示用户生成一条未来预约 + 一条已完成并评价的历史预约。"""
    service = db.session.scalar(
        select(ServiceItem).where(ServiceItem.name == "身份证换领办理")
    )
    has_appointment = db.session.scalar(
        select(Appointment.id).where(Appointment.user_id == user_id).limit(1)
    )
    if service is None or has_appointment is not None:
        return

    db.session.add(Appointment(
        user_id=user_id,
        service_id=service.id,
        appointment_date=date.today() + timedelta(days=1),
        time_slot="09:00-10:00",
        contact_name="张三",
        contact_phone="13800138000",
        status="confirmed",
    ))
    created["appointments"] += 1

    finished = Appointment(
        user_id=user_id,
        service_id=service.id,
        appointment_date=date.today() - timedelta(days=7),
        time_slot="10:00-11:00",
        contact_name="张三",
        contact_phone="13800138000",
        status="completed",
    )
    db.session.add(finished)
    db.session.flush()
    created["appointments"] += 1
    db.session.add(Feedback(
        user_id=user_id,
        service_id=service.id,
        appointment_id=finished.id,
        rating=5,
        content="办理速度快，工作人员态度很好。",
    ))
    created["feedbacks"] += 1


def seed_demo_data():
    """写入演示数据，返回本次实际新增的条数（幂等，可重复执行）。"""
    created = {"users": 0, "services": 0, "announcements": 0, "appointments": 0, "feedbacks": 0}
    try:
        admin, zhangsan = _seed_users(created)
        _seed_services(created)
        _seed_announcements(created, admin.id)
        _seed_appointments(created, zhangsan.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return created
