"""契约式编程单元测试（教材 4.3.2 断言三分类 + 4.9.3 契约三要素）。

覆盖点：
  1. require / ensure / invariant 三类断言在违约时抛 ContractViolation（AssertionError 子类）；
  2. 契约检查可通过环境变量关闭（对应"程序部署完之后就关闭断言"）；
  3. 业务函数在合法输入下不违约（契约不改变正常行为）；
  4. 业务函数在调用方违约时立即失败（fail-fast，而不是返回错误数据）。
"""
import pytest

from app.services.appointment_rules import (
    AppointmentContext,
    is_valid_slot,
    next_statuses,
    remaining_capacity,
    validate_new_appointment,
)
from app.utils.contracts import ContractViolation, contract, contracts_enabled, ensure, invariant, require
from datetime import date


# ------------------------------------------------------------------ 1. 三类断言
def test_require_passes_when_condition_true():
    assert require(1 < 2, "1 应小于 2") is True


def test_require_raises_on_violation():
    with pytest.raises(ContractViolation) as exc:
        require(2 < 1, "前置条件：a 必须小于 b")
    assert "前置条件" in str(exc.value)
    assert isinstance(exc.value, AssertionError)  # 与内置断言语义一致


def test_ensure_raises_on_violation():
    with pytest.raises(ContractViolation) as exc:
        ensure(False, "后置条件：返回值必须为正")
    assert "后置条件" in str(exc.value)


def test_invariant_raises_on_violation():
    with pytest.raises(ContractViolation) as exc:
        invariant(False, "不变式：时段表不得被修改")
    assert "不变式" in str(exc.value)


def test_contract_can_be_disabled(monkeypatch):
    """关闭断言后违约不抛异常：对应教材"部署完之后关闭断言"的工程实践。"""
    monkeypatch.setenv("CONTRACT_CHECK", "0")
    assert contracts_enabled() is False
    assert require(False, "关闭后不检查") is True
    assert ensure(False, "关闭后不检查") is True
    assert invariant(False, "关闭后不检查") is True


def test_contract_decorator_binds_pre_and_post():
    @contract(pre=lambda a, k: a[0] >= 0, post=lambda a, k, r: r >= 0)
    def sqrt_like(x):
        """返回输入值（演示契约装饰器）"""
        return x

    assert sqrt_like(4) == 4
    with pytest.raises(ContractViolation):
        sqrt_like(-1)


# ------------------------------------------------------------------ 2. 业务函数契约
def test_remaining_capacity_contract_rejects_negative():
    with pytest.raises(ContractViolation):
        remaining_capacity(-1, 0)
    with pytest.raises(ContractViolation):
        remaining_capacity(5, -2)


def test_remaining_capacity_contract_rejects_non_integer():
    with pytest.raises(ContractViolation):
        remaining_capacity(5.0, 2)


def test_remaining_capacity_postcondition_holds_for_all_valid_inputs():
    """后置条件：0 <= 返回值 <= capacity，对全部合法输入穷举成立。"""
    for capacity in range(0, 6):
        for used in range(0, 9):
            remain = remaining_capacity(capacity, used)
            assert 0 <= remain <= capacity


def test_is_valid_slot_contract_rejects_wrong_type():
    with pytest.raises(ContractViolation):
        is_valid_slot(123)


def test_validate_new_appointment_rejects_wrong_context():
    with pytest.raises(ContractViolation):
        validate_new_appointment({"service_online": True}, date.today(), "09:00-10:00")


def test_validate_new_appointment_rejects_bad_max_days():
    ctx = AppointmentContext(service_online=True, capacity=5, used=0)
    with pytest.raises(ContractViolation):
        validate_new_appointment(ctx, date.today(), "09:00-10:00", max_days_ahead=0)


def test_validate_new_appointment_postcondition_returns_non_empty_strings():
    """后置条件：返回列表，且其中每条错误都是非空字符串。"""
    ctx = AppointmentContext(service_online=False, capacity=0, used=5, has_duplicate=True)
    errors = validate_new_appointment(ctx, None, "bad-slot")
    assert isinstance(errors, list) and errors
    assert all(isinstance(e, str) and e.strip() for e in errors)
    # 四个错误分别来自：服务下架、未选日期（提前返回）——不变量仍成立
    assert any("下架" in e for e in errors)
    assert any("选择预约日期" in e for e in errors)


def test_state_query_contract_requires_string():
    with pytest.raises(ContractViolation):
        next_statuses(None)
