"""黑盒测试 · 因果图法（教材 10.3）。

教材步骤（《软件质量保证与测试》第 2 版 10.3.1）：
  (1) 从规格说明中找出原因（输入条件）与结果（输出或状态改变）；
  (2) 画出连接原因与结果的因果图；
  (3) 标明约束条件（E 互斥 / I 包含 / O 唯一 / R 要求 / M 屏蔽）；
  (4) 把因果图转换成判定表；
  (5) 为判定表每一列设计一个测试用例。

被测功能：在线预约提交（POST /appointments/create/<service_id> → 业务层 create_appointment）。

原因与结果编号
--------------
原因 C1 服务处于上架状态         结果 E1 预约创建成功（落库 + 跳转"我的预约"）
C2 已选择预约日期                E2 提示"服务不存在或已下架"
C3 日期不早于今天且在 30 天内     E3 提示日期类错误（过去 / 超过 30 天 / 未选）
C4 时段属于开放时段表            E4 提示"预约时段无效"
C5 联系人姓名 >= 2 字            E5 提示姓名/手机号格式错误
C6 手机号符合 1[3-9]\\d{9}        E6 提示"请勿重复提交"
C7 该用户在该时段无有效预约       E7 提示"名额已满"
C8 该时段剩余名额 > 0

约束
----
· R（要求）：C3 出现要求 C2 出现 —— 未选日期时"日期是否合法"无意义；
· E（互斥）：E2~E7 在一次请求中可同时出现多条 flash，但"成功 E1"与任一失败结果互斥；
· M（屏蔽）：C5/C6 不满足时，表单校验先行返回，业务规则（C3/C4/C7/C8）不再被求值。

判定表共 12 列，每列一个用例；其中第 2~5 列专门覆盖 C2/C3 的 R 约束与日期边界。
"""
from datetime import date, timedelta

import pytest
from app.extensions import db
from app.models import Appointment, ServiceItem, User
from app.services.appointment_service import create_appointment

# 日期一律相对「今天」构造，避免用例随系统日期推移而失效：
# 若写死某一天，跨天后 TOMORROW 会变成今天或过去，被「已开始时段不可约」规则正确拦截，
# 导致判定表用例出现假失败（2026-11-24 实测 6 条失败）。测试必须与运行时刻无关。
TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)
SLOT = "09:00-10:00"


def _user(app=None, username="co_user", email="co@example.com"):
    user = User(username=username, email=email)
    user.set_password("User@123")
    db.session.add(user)
    db.session.commit()
    return user


def _service(app, capacity=2, status="online"):
    item = ServiceItem(
        name="因果图测试服务",
        category="life",
        description="用于因果图法验证的测试服务。",
        address="测试地址",
        price=10,
        duration_minutes=30,
        daily_capacity=capacity,
        status=status,
    )
    db.session.add(item)
    db.session.commit()
    return item


def _fill_capacity(service, day, slot, n):
    """用其他用户占满 n 个名额。"""
    for i in range(n):
        other = _user(username=f"filler{i}", email=f"filler{i}@example.com")
        db.session.add(
            Appointment(
                user_id=other.id,
                service_id=service.id,
                appointment_date=day,
                time_slot=slot,
                contact_name="占位用户",
                contact_phone="13900139000",
                status="pending",
            )
        )
    db.session.commit()


# 判定表：每行 = 一列，字段为 8 个原因的取值；expect 为期望结果标识
DECISION_TABLE = [
    # id, C1..C8, 期望
    ("COL-1", (1, 1, 1, 1, 1, 1, 1, 1), "E1"),
    ("COL-2", (0, 1, 1, 1, 1, 1, 1, 1), "E2"),
    ("COL-3", (1, 0, 0, 1, 1, 1, 1, 1), "E3-未选"),
    ("COL-4", (1, 1, 0, 1, 1, 1, 1, 1), "E3-过去"),
    ("COL-5", (1, 1, 0, 1, 1, 1, 1, 1), "E3-超期"),
    ("COL-6", (1, 1, 1, 0, 1, 1, 1, 1), "E4"),
    ("COL-7", (1, 1, 1, 1, 0, 1, 1, 1), "E5-姓名"),
    ("COL-8", (1, 1, 1, 1, 1, 0, 1, 1), "E5-手机"),
    ("COL-9", (1, 1, 1, 1, 1, 1, 0, 1), "E6"),
    ("COL-10", (1, 1, 1, 1, 1, 1, 1, 0), "E7"),
    ("COL-11", (1, 1, 1, 1, 0, 0, 1, 1), "E5-双错"),
    ("COL-12", (1, 1, 1, 1, 1, 1, 0, 0), "E6+E7"),
]


def _run_column(app, column_id, causes, expect):
    """按判定表的一列构造输入并断言输出（每次用干净库）。"""
    c1, c2, c3, c4, c5, c6, c7, c8 = causes
    user = _user(app)
    service = _service(app, capacity=2, status="online" if c1 else "offline")

    day = TOMORROW
    if c3 == 0 and expect == "E3-过去":
        day = TODAY - timedelta(days=1)
    elif c3 == 0 and expect == "E3-超期":
        day = TODAY + timedelta(days=31)
    if c2 == 0:
        day = None

    slot = SLOT if c4 else "25:00-26:00"

    if c7 == 0:
        db.session.add(
            Appointment(user_id=user.id, service_id=service.id, appointment_date=day or TOMORROW,
                        time_slot=slot, contact_name="张三", contact_phone="13800138000",
                        status="pending")
        )
        db.session.commit()
    if c8 == 0:
        _fill_capacity(service, day or TOMORROW, slot, 2)

    name = "张三" if c5 else "张"
    phone = "13800138000" if c6 else "12345"

    appointment, errors = create_appointment(
        user=user, service_id=service.id, appointment_date=day, time_slot=slot,
        contact_name=name, contact_phone=phone, remark="因果图用例",
    )

    if expect == "E1":
        assert errors == []
        assert appointment is not None and appointment.id is not None
        assert db.session.get(Appointment, appointment.id) is not None
        return
    assert appointment is None, f"{column_id} 不应创建预约"
    assert errors, f"{column_id} 应给出错误提示"
    joined = " ".join(errors)

    if expect == "E2":
        # 业务层提示"该服务已下架，暂不可预约"；视图层提示"不存在或已下架"，同属 E2
        assert "下架" in joined
    elif expect == "E3-未选":
        assert "请选择预约日期" in joined
    elif expect == "E3-过去":
        assert "过去的日期" in joined
    elif expect == "E3-超期":
        assert "30 天" in joined
    elif expect == "E4":
        assert "时段无效" in joined
    elif expect == "E5-姓名":
        assert "真实姓名" in joined
    elif expect == "E5-手机":
        assert "手机号" in joined
    elif expect == "E5-双错":
        assert "真实姓名" in joined and "手机号" in joined
    elif expect == "E6":
        assert "重复" in joined
    elif expect == "E7":
        assert "名额已满" in joined
    elif expect == "E6+E7":
        # 判定表中 E6/E7 可同时成立：两条提示都应出现
        assert "重复" in joined and "名额已满" in joined
    else:  # pragma: no cover
        raise AssertionError(f"未知期望 {expect}")


@pytest.mark.parametrize("column_id,causes,expect", DECISION_TABLE,
                         ids=[c[0] for c in DECISION_TABLE])
def test_decision_table_columns(app, column_id, causes, expect):
    """判定表逐列执行：每列一个测试用例（教材 10.3.1 第 5 步）。"""
    _run_column(app, column_id, causes, expect)


def test_constraint_R_c3_requires_c2():
    """约束 R（要求）：C3 出现要求 C2 出现。

    因此判定表中"C2=0 且 C3=1"这一列在因果图中**不可达**，不应设计用例。
    这里用集合运算验证：可达列数 < 原因组合的理论总数。
    """
    reachable = [c for c in DECISION_TABLE if not (c[1][1] == 0 and c[1][2] == 1)]
    assert len(reachable) == len(DECISION_TABLE)  # 判定表本身已剔除不可达列
    assert len(DECISION_TABLE) < 2 ** 8           # 未做全组合爆炸，靠约束剪枝


def test_constraint_M_form_errors_mask_business_rules(app):
    """约束 M（屏蔽）：姓名/手机号非法时，业务规则不再求值——即使时段非法也只报字段错误。"""
    user = _user(app, username="mask_user", email="mask@example.com")
    service = _service(app)
    appointment, errors = create_appointment(
        user=user, service_id=service.id, appointment_date=TOMORROW, time_slot="25:00-26:00",
        contact_name="张", contact_phone="12345",
    )
    assert appointment is None
    joined = " ".join(errors)
    assert "真实姓名" in joined and "手机号" in joined
    assert "时段无效" not in joined  # 被屏蔽，未求值


def test_effect_exclusivity_success_vs_failure(app):
    """互斥约束 E：同一请求要么成功（E1），要么至少一条失败结果，二者不可并存。"""
    user = _user(app, username="ex_user", email="ex@example.com")
    service = _service(app, status="offline")
    appointment, errors = create_appointment(
        user=user, service_id=service.id, appointment_date=TOMORROW, time_slot=SLOT,
        contact_name="张三", contact_phone="13800138000",
    )
    assert (appointment is None) != (errors == [])
