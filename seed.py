"""演示数据脚本：初始化管理员、普通用户、服务项目、公告、预约与评价。

用法：python run.py --init-db --seed
"""
from datetime import date, timedelta

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


def seed_demo_data():
    """写入演示数据（可重复执行：已存在同名数据时跳过）。"""
    # 1) 用户
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", email="admin@example.com", real_name="系统管理员", role="admin")
        admin.set_password("Admin@123")
        db.session.add(admin)
    if not User.query.filter_by(username="zhangsan").first():
        zhangsan = User(username="zhangsan", email="zhangsan@example.com",
                        real_name="张三", phone="13800138000", role="user")
        zhangsan.set_password("User@123")
        db.session.add(zhangsan)
    db.session.commit()

    admin = User.query.filter_by(username="admin").first()
    zhangsan = User.query.filter_by(username="zhangsan").first()

    # 2) 服务项目
    for item in SERVICES:
        if ServiceItem.query.filter_by(name=item["name"]).first():
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
    db.session.commit()

    # 3) 公告
    for ann in ANNOUNCEMENTS:
        if Announcement.query.filter_by(title=ann["title"]).first():
            continue
        db.session.add(Announcement(
            title=ann["title"], content=ann["content"], author_id=admin.id, is_published=True
        ))
    db.session.commit()

    # 4) 一条示例预约（明天上午）+ 已完成并评价的预约
    service = ServiceItem.query.filter_by(name="身份证换领办理").first()
    if service and not Appointment.query.filter_by(user_id=zhangsan.id).first():
        tomorrow = date.today() + timedelta(days=1)
        appt = Appointment(
            user_id=zhangsan.id,
            service_id=service.id,
            appointment_date=tomorrow,
            time_slot="09:00-10:00",
            contact_name="张三",
            contact_phone="13800138000",
            status="confirmed",
        )
        db.session.add(appt)
        db.session.commit()

        old = Appointment(
            user_id=zhangsan.id,
            service_id=service.id,
            appointment_date=date.today() - timedelta(days=7),
            time_slot="10:00-11:00",
            contact_name="张三",
            contact_phone="13800138000",
            status="completed",
        )
        db.session.add(old)
        db.session.commit()
        db.session.add(Feedback(
            user_id=zhangsan.id, service_id=service.id, appointment_id=old.id,
            rating=5, content="办理速度快，工作人员态度很好。"
        ))
        db.session.commit()
    print("演示数据：admin/Admin@123（管理员）、zhangsan/User@123（普通用户）")


if __name__ == "__main__":
    from app import create_app

    app = create_app("development")
    with app.app_context():
        db.create_all()
        seed_demo_data()
