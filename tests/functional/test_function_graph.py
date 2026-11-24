"""黑盒测试 · 功能图法（教材 10.4）。

教材要点（10.4.1）：功能图模型 = **状态迁移图**（动态说明：输入序列与状态改变）
+ **逻辑功能模型**（静态说明：状态内输入条件与输出条件的对应关系）。
测试用例 = 一条"状态序列" + 每个状态上的"输入/输出条件对"，生成步骤如下：
  (1) 在每个状态中用判定表生成局部测试用例；
  (2) 在状态迁移图中生成从初始状态到终止状态的测试路径；
  (3) 合成路径与局部用例（教材采用条件构造树，此处用参数化路径 + 判定表实现）。

被测对象：预约状态机（pending → confirmed → completed / cancelled）。
状态迁移图：
        ┌──────────── 取消 ────────────┐
        ↓                              │
   [pending] ──确认──> [confirmed] ──完成──> [completed]（终态）
        │                    │
        └──── 取消 ──────────┴────> [cancelled]（终态）

逻辑功能模型（每个状态的局部判定表）：
    状态       | 目标状态   | 操作者   | 期望
    pending    | confirmed  | 管理员   | 允许
    pending    | completed  | 管理员   | 拒绝（跳步）
    pending    | cancelled  | 本人     | 允许
    confirmed  | completed  | 管理员   | 允许
    confirmed  | cancelled  | 本人     | 允许
    confirmed  | pending    | 管理员   | 拒绝（回退）
    completed  | *          | 管理员   | 拒绝（终态）
    cancelled  | *          | 管理员   | 拒绝（终态）
"""
from datetime import timedelta

import pytest
from app.extensions import db
from app.models import Appointment
from app.services.appointment_service import cancel_appointment, change_status

# ---------------------------------------------------------------- 状态迁移图路径
PATHS = [
    # (路径编号, 状态序列, 期望最终状态, 期望各步成功)
    ("P1", ["pending", "confirmed", "completed"], "completed", [True, True]),
    ("P2", ["pending", "confirmed", "cancelled"], "cancelled", [True, True]),
    ("P3", ["pending", "cancelled"], "cancelled", [True]),
    ("P4", ["pending", "completed"], "pending", [False]),          # 跳步：非法
    ("P5", ["confirmed", "pending"], "confirmed", [False]),        # 回退：非法
    ("P6", ["completed", "cancelled"], "completed", [False]),      # 终态出发：非法
    ("P7", ["cancelled", "confirmed"], "cancelled", [False]),      # 终态出发：非法
]


def _make_appointment(app, user, service, status="pending"):
    appt = Appointment(
        user_id=user.id,
        service_id=service.id,
        appointment_date=appt_date(),
        time_slot="09:00-10:00",
        contact_name="张三",
        contact_phone="13800138000",
        status=status,
    )
    db.session.add(appt)
    db.session.commit()
    return appt


def appt_date():
    from datetime import date

    return date.today() + timedelta(days=1)


@pytest.mark.parametrize("path_id,states,expected_final,expectations", PATHS,
                         ids=[p[0] for p in PATHS])
def test_state_migration_paths(app, normal_user, admin_user, service,
                               path_id, states, expected_final, expectations):
    """在状态迁移图上走一条路径，逐步校验局部判定表的期望。"""
    appt = _make_appointment(app, normal_user, service, status=states[0])
    results = []
    for target in states[1:]:
        if target == "cancelled":
            ok, _ = cancel_appointment(appt, normal_user)
        else:
            ok, _ = change_status(appt, target)
        results.append(ok)
        db.session.refresh(appt)

    assert results == expectations, f"{path_id} 的状态迁移结果与功能图不符"
    assert appt.status == expected_final


# ---------------------------------------------------------------- 局部逻辑功能模型
LOCAL_TABLE = [
    # 状态, 操作, 操作者, 期望允许
    ("pending", "confirm", "admin", True),
    ("pending", "complete", "admin", False),
    ("pending", "cancel", "owner", True),
    ("pending", "cancel", "other", False),
    ("confirmed", "complete", "admin", True),
    ("confirmed", "cancel", "owner", True),
    ("confirmed", "back_to_pending", "admin", False),
    ("completed", "cancel", "owner", False),
    ("completed", "confirm", "admin", False),
    ("cancelled", "confirm", "admin", False),
]


@pytest.mark.parametrize("state,action,actor,allowed", LOCAL_TABLE,
                         ids=[f"{s}-{a}-{who}" for s, a, who, _ in LOCAL_TABLE])
def test_local_logic_model(app, normal_user, admin_user, service,
                           state, action, actor, allowed):
    """每个状态内部的局部判定表：输入（操作、操作者）+ 当前状态 → 输出（允许/拒绝）。"""
    appt = _make_appointment(app, normal_user, service, status=state)

    if action == "cancel":
        operator = normal_user
        if actor == "other":
            from app.models import User

            other = User(username="other_user", email="other@example.com")
            other.set_password("User@123")
            db.session.add(other)
            db.session.commit()
            operator = other
        ok, message = cancel_appointment(appt, operator)
    else:
        target = {"confirm": "confirmed", "complete": "completed",
                  "back_to_pending": "pending"}[action]
        ok, message = change_status(appt, target)

    assert ok is allowed, f"{state}/{action}/{actor} 期望 allowed={allowed}，实际消息：{message}"
    db.session.refresh(appt)
    if not allowed:
        assert appt.status == state  # 拒绝时状态不得改变（不变量）


def test_path_and_local_cases_compose(app, normal_user, admin_user, service):
    """合成用例：路径 P3（pending→cancelled）的每一步同时满足局部判定表。"""
    appt = _make_appointment(app, normal_user, service, status="pending")
    assert appt.status == "pending"
    ok, _ = cancel_appointment(appt, normal_user)
    assert ok and appt.status == "cancelled"
    # 终态的局部判定表：不允许再确认
    ok2, message = change_status(appt, "confirmed")
    assert not ok2 and "不允许" in message
