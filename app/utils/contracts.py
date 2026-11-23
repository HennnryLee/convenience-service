"""契约式编程（Design by Contract）支撑工具。

对齐《基于案例的软件构造教程》：
  · 4.3.2 使用断言：断言分为**前置断言 / 后置断言 / 不变断言**三类；
  · 4.9.3 契约式编程：用"三个问题"描述一个模块 ——
        它期望的是什么（前置条件，客户的义务）？
        它保证的是什么（后置条件，供应商的义务）？
        它要保持的是什么（不变式，进入时假定、退出时保持）？

本模块把断言从"零散写在函数里的 assert"提升为一层可复用的契约声明：
  - require(...)  前置条件：调用方必须先满足的条件，不满足即调用方违约；
  - ensure(...)   后置条件：被调方承诺的交付结果，不满足即实现违约；
  - invariant(...) 不变式：执行前后都必须成立的性质（如全局表不被篡改）。

设计取舍：
  1. 违约抛 ContractViolation（继承 AssertionError），与 Python 内置断言语义一致；
  2. 契约检查可整体关闭（环境变量 CONTRACT_CHECK=0）——对应教材"程序部署完之后就关闭断言"，
     关闭后不执行条件求值，不带来运行期开销；
  3. 契约只用于检查**程序内部的错误**（不应当出现的条件），用户输入错误一律走错误处理，
     对应教材"对预计出现的条件使用错误处理，对不应当出现的条件使用断言"。
"""
from __future__ import annotations

import functools
import os


class ContractViolation(AssertionError):
    """契约违约。继承 AssertionError，便于用 pytest.raises(AssertionError) 统一捕获。"""


def contracts_enabled():
    """契约检查开关：默认开启，设置环境变量 CONTRACT_CHECK=0 可关闭（模拟发布版）。"""
    return os.environ.get("CONTRACT_CHECK", "1") != "0"


def require(condition, message):
    """前置条件（precondition）：调用方必须满足的义务。"""
    if contracts_enabled() and not condition:
        raise ContractViolation(f"前置条件不满足：{message}")
    return True


def ensure(condition, message):
    """后置条件（postcondition）：被调方必须保证的结果。"""
    if contracts_enabled() and not condition:
        raise ContractViolation(f"后置条件不满足：{message}")
    return True


def invariant(condition, message):
    """不变式（invariant）：执行前后都必须成立的性质。"""
    if contracts_enabled() and not condition:
        raise ContractViolation(f"不变式被破坏：{message}")
    return True


def contract(pre=None, post=None, inv=None):
    """把契约声明为装饰器（可选用法）。

    pre/post 接受 (args, kwargs, result) 中的一部分参数，返回布尔值的可调用对象：
        pre(args, kwargs)             -> bool
        post(args, kwargs, result)    -> bool
        inv(args, kwargs, result)     -> bool
    违约信息取被装饰函数的 docstring 首行，便于定位。
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = (func.__doc__ or func.__name__).strip().splitlines()[0]
            if pre is not None:
                require(pre(args, kwargs), f"{func.__name__}(): {name}")
            result = func(*args, **kwargs)
            if post is not None:
                ensure(post(args, kwargs, result), f"{func.__name__}(): {name}")
            if inv is not None:
                invariant(inv(args, kwargs, result), f"{func.__name__}(): {name}")
            return result

        return wrapper

    return decorator
