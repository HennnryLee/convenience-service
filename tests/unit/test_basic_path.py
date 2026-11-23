"""白盒测试 · 基本路径测试法（教材 11.3）。

教材步骤：
  第一步 画出控制流图（判断中的复合条件要拆成单条件嵌套判断）；
  第二步 计算圈复杂度 V(G)：① 区域数  ② V(G)=E−N+2  ③ V(G)=P+1；
  第三步 导出基本路径集（独立路径至少引入一条新边）；
  第四步 为每条路径准备测试用例。

被测单元：`cancel_appointment`（取消预约，含 3 个判定，其中 1 个复合条件）。
控制流图（END 为合并后的唯一出口，便于套用 E−N+2 公式）：

    N1(入口) → N2{appointment 为 None?}
                 ├─T→ N3[不存在] ─────────────┐
                 └─F→ N4{非管理员 且 非本人?}  │
                        ├─T→ N5[只能取消本人] ─┤
                        └─F→ N6{状态可取消?}   │
                               ├─T→ N7[不可取消]┤
                               └─F→ N8[执行取消]┤
                                                └→ N9(END)
"""
from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import Appointment, User
from app.services.appointment_service import cancel_appointment

# ---------------------------------------------------------------- 控制流图数据
NODES = ["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9"]
EDGES = [
    ("N1", "N2"),
    ("N2", "N3"), ("N2", "N4"),
    ("N4", "N5"), ("N4", "N6"),
    ("N6", "N7"), ("N6", "N8"),
    ("N3", "N9"), ("N5", "N9"), ("N7", "N9"), ("N8", "N9"),
]
PREDICATE_NODES = ["N2", "N4", "N6"]


def test_cyclomatic_complexity_two_formulas_agree():
    """V(G) 用两种公式交叉验证：E−N+2 与 P+1 必须相等（教材 11.3.2）。"""
    v_by_edges = len(EDGES) - len(NODES) + 2
    v_by_predicates = len(PREDICATE_NODES) + 1
    assert v_by_edges == v_by_predicates == 4


def test_basic_path_set_is_independent():
    """基本路径集：每条路径至少引入一条此前未用过的边。"""
    paths = {
        "P1": ["N1", "N2", "N3", "N9"],
        "P2": ["N1", "N2", "N4", "N5", "N9"],
        "P3": ["N1", "N2", "N4", "N6", "N7", "N9"],
        "P4": ["N1", "N2", "N4", "N6", "N8", "N9"],
    }
    assert len(paths) == len(PREDICATE_NODES) + 1  # 路径数 = V(G)

    used = set()
    for name, path in paths.items():
        path_edges = set(zip(path, path[1:]))
        new_edges = path_edges - used
        assert new_edges, f"{name} 没有引入新边，不是独立路径"
        used |= path_edges
    # 所有边都被基本路径集覆盖
    assert used == set(EDGES)


# ---------------------------------------------------------------- 为每条路径准备用例
def _fixtures(app, owner=True, status="pending"):
    user = User(username="bp_owner", email="bp@example.com")
    other = User(username="bp_other", email="bp_other@example.com")
    for u in (user, other):
        u.set_password("User@123")
        db.session.add(u)
    db.session.commit()

    from app.models import ServiceItem

    service = ServiceItem(name="基本路径服务", category="life", description="d",
                          address="a", price=1, duration_minutes=30, daily_capacity=2,
                          status="online")
    db.session.add(service)
    db.session.commit()

    appt = Appointment(
        user_id=user.id, service_id=service.id,
        appointment_date=date.today() + timedelta(days=1),
        time_slot="09:00-10:00", contact_name="张三", contact_phone="13800138000",
        status=status,
    )
    db.session.add(appt)
    db.session.commit()
    return user, other, appt


def test_path_1_record_not_found(app):
    """P1：N1→N2(T)→N3→N9，预约记录不存在。"""
    ok, message = cancel_appointment(None, operator=None)
    assert ok is False and "不存在" in message


def test_path_2_non_owner_rejected(app):
    """P2：N1→N2(F)→N4(T)→N5→N9，普通用户取消他人预约。"""
    owner, other, appt = _fixtures(app)
    ok, message = cancel_appointment(appt, other)
    assert ok is False and "本人" in message
    db.session.refresh(appt)
    assert appt.status == "pending"


def test_path_3_terminal_status_rejected(app):
    """P3：N1→N2(F)→N4(F)→N6(T)→N7→N9，本人取消处于终态的预约。"""
    owner, _, appt = _fixtures(app, status="completed")
    ok, message = cancel_appointment(appt, owner)
    assert ok is False and "不可取消" in message


def test_path_4_success(app):
    """P4：N1→N2(F)→N4(F)→N6(F)→N8→N9，本人取消待确认预约。"""
    owner, _, appt = _fixtures(app)
    ok, message = cancel_appointment(appt, owner)
    assert ok is True and "已取消" in message
    db.session.refresh(appt)
    assert appt.status == "cancelled"


def test_compound_condition_short_circuit_paths(app):
    """复合条件 N4 = `not is_admin and user_id != operator.id` 的两种取值组合：

    (T,T) 普通用户取消他人 → 拒绝（P2）
    (F,-) 管理员取消他人   → 短路，进入 N6（教材要求复合条件拆成单条件判断）
    """
    owner, other, appt = _fixtures(app)
    admin = User(username="bp_admin", email="bp_admin@example.com", role="admin")
    admin.set_password("Admin@123")
    db.session.add(admin)
    db.session.commit()

    ok, message = cancel_appointment(appt, admin, is_admin=True)
    assert ok is True, message
    db.session.refresh(appt)
    assert appt.status == "cancelled"
