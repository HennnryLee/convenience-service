"""黑盒测试 · 边界值分析：服务查询（关键词）功能。

被测：GET /services/?keyword=...
边界：长度 0（空）、1、50、51，以及特殊字符、无匹配两种异常输入。
"""
from app.config import Config
from app.models import ServiceItem


def make_service(name, category="life", **kw):
    payload = dict(name=name, category=category, description=name + "的描述",
                   address="测试地址", price=10, duration_minutes=30,
                   daily_capacity=5, status="online")
    payload.update(kw)
    return ServiceItem(**payload)


def test_keyword_empty_returns_all(client, app):
    """边界值：关键词为空 → 返回全部在线服务。"""
    from app.extensions import db

    db.session.add_all([make_service("服务A"), make_service("服务B")])
    db.session.commit()
    resp = client.get("/services/?keyword=")
    assert resp.status_code == 200
    assert "服务A".encode() in resp.data and "服务B".encode() in resp.data


def test_keyword_length_1(client, app):
    """边界值：关键词长度为 1 → 正常检索。"""
    from app.extensions import db

    db.session.add(make_service("管道疏通"))
    db.session.commit()
    resp = client.get("/services/?keyword=" + "管")
    assert resp.status_code == 200
    assert "管道疏通".encode() in resp.data


def test_keyword_length_50_accepted(client, app):
    """边界值：关键词长度 = 50（上限）→ 正常执行，不报错。"""
    from app.extensions import db

    db.session.add(make_service("长关键词服务"))
    db.session.commit()
    keyword = "关" * 50
    assert len(keyword) == Config.MAX_SEARCH_KEYWORD
    resp = client.get("/services/?keyword=" + keyword)
    assert resp.status_code == 200
    assert "不能超过".encode() not in resp.data


def test_keyword_length_51_rejected(client, app):
    """边界值：关键词长度 = 51（上限+1）→ 提示超长且不返回服务列表。"""
    from app.extensions import db

    db.session.add(make_service("超长关键词服务"))
    db.session.commit()
    keyword = "关" * 51
    resp = client.get("/services/?keyword=" + keyword)
    assert resp.status_code == 200
    assert f"不能超过 {Config.MAX_SEARCH_KEYWORD}".encode() in resp.data
    assert "超长关键词服务".encode() not in resp.data


def test_keyword_no_match_shows_tip(client, app):
    """异常输入：无匹配结果 → 给出"没有找到匹配的服务"提示。"""
    from app.extensions import db

    db.session.add(make_service("管道疏通"))
    db.session.commit()
    resp = client.get("/services/?keyword=" + "不存在的服务名称")
    assert resp.status_code == 200
    assert "没有找到匹配的服务".encode() in resp.data


def test_keyword_with_sql_injection_is_safe(client, app):
    """异常输入 + 安全性：SQL 注入串被当作普通字符串，系统正常运行且不报错。"""
    from app.extensions import db

    db.session.add(make_service("社保卡申领"))
    db.session.commit()
    resp = client.get("/services/?keyword=" + "' OR '1'='1")
    assert resp.status_code == 200        # 不出现 500
    assert "社保卡申领".encode() not in resp.data  # 注入未生效，返回空结果


def test_keyword_with_xss_payload_is_escaped(client, app):
    """异常输入 + 安全性：XSS 载荷被 Jinja2 自动转义，不会以可执行形式输出。"""
    from app.extensions import db

    db.session.add(make_service("<script>alert(1)</script>服务"))
    db.session.commit()
    resp = client.get("/services/?keyword=" + "<script>")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "<script>alert(1)</script>" not in body   # 被转义为 &lt;script&gt;
    assert "&lt;script&gt;" in body


def test_keyword_percent_is_literal(client, app):
    """DEF-001 回归：关键词中的 % 只匹配字面量，不再被 LIKE 当作通配符。

    修复前该用例会返回全部服务；修复后只有名称/简介真正包含 % 的服务命中。
    """
    from app.extensions import db

    db.session.add_all([
        make_service("服务甲"),
        make_service("服务乙"),
        make_service("折扣100%服务"),
    ])
    db.session.commit()

    resp = client.get("/services/", query_string={"keyword": "%"})
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "折扣100%服务" in body
    assert "服务甲" not in body and "服务乙" not in body


def test_keyword_underscore_is_literal(client, app):
    """DEF-001 同类边界：LIKE 的 _ 通配符也必须转义。"""
    from app.extensions import db

    db.session.add_all([
        make_service("普通服务"),
        make_service("下划线_服务"),
    ])
    db.session.commit()

    resp = client.get("/services/", query_string={"keyword": "_"})
    body = resp.get_data(as_text=True)
    assert "下划线_服务" in body
    assert "普通服务" not in body


def test_keyword_backslash_is_literal(client, app):
    """转义字符本身也应作为普通字符处理，不破坏查询。"""
    from app.extensions import db

    db.session.add_all([make_service("反斜杠\\服务"), make_service("普通服务")])
    db.session.commit()

    resp = client.get("/services/", query_string={"keyword": "\\"})
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "反斜杠\\服务" in body
    assert "普通服务" not in body
