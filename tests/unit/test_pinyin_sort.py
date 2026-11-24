"""拼音排序键与"按名称"排序的回归测试。

背景：原实现是 ORDER BY name ASC，SQLite 默认 BINARY 排序规则按 UTF-8 字节
比较，中文排出来是 Unicode 码点序（住 → 儿 → 家 → 成 …），既不是拼音也不是
笔画。用户看到"按名称"排成这样会认为功能坏了（人工 β 测试提出）。

修复：写入时生成 name_pinyin（音节间单空格分隔），排序比较该列，
不再依赖具体数据库的 collation 实现。
"""
import pytest
from app.extensions import db
from app.models import ServiceItem
from app.repositories.service_repository import ServiceRepository
from app.utils.pinyin import PINYIN_KEY_MAX_LENGTH, to_pinyin_key


def make_service(name, **kw):
    payload = dict(
        name=name,
        category="life",
        description=name,
        address="测试地址",
        price=10,
        duration_minutes=30,
        daily_capacity=5,
        status="online",
    )
    payload.update(kw)
    return ServiceItem(**payload)


# ------------------------------------------------------------------ 纯函数
@pytest.mark.parametrize(
    "text, expected",
    [
        (None, ""),
        ("", ""),
        ("管道疏通", "guan dao shu tong"),
        ("重庆火锅", "chong qing huo guo"),
        ("银行", "yin hang"),
        ("iPhone 15 维修", "iphone 15 wei xiu"),
        ("24小时服务", "24 xiao shi fu wu"),
        ("服务（含材料）", "fu wu han cai liao"),
    ],
)
def test_to_pinyin_key(text, expected):
    assert to_pinyin_key(text) == expected


def test_polysyllabic_word_is_disambiguated():
    """多音字按词组上下文取音：重庆是 chong，重要是 zhong。"""
    assert to_pinyin_key("重庆").startswith("chong")
    assert to_pinyin_key("重要").startswith("zhong")


def test_syllable_boundary_is_preserved():
    """音节边界必须参与比较：she bao < she qu < shen fen。

    若直接拼成无分隔串，会按字符比成 shebao < shenfen < shequ，
    把"身份证"插到两个"社"中间，与拼音字典序不符。
    """
    keys = [to_pinyin_key(name) for name in ("社保卡", "社区", "身份证")]
    assert keys == sorted(keys)


def test_key_length_is_bounded():
    assert len(to_pinyin_key("服" * 100)) <= PINYIN_KEY_MAX_LENGTH


# ------------------------------------------------------------------ 模型层
def test_model_generates_key_on_create(app):
    item = make_service("管道疏通")
    db.session.add(item)
    db.session.commit()
    assert item.name_pinyin == "guan dao shu tong"


def test_model_refreshes_key_when_name_changes(app):
    item = make_service("管道疏通")
    db.session.add(item)
    db.session.commit()

    item.name = "社区洗衣干洗"
    db.session.commit()
    assert item.name_pinyin == "she qu xi yi gan xi"


def test_repository_update_refreshes_key(app, service):
    ServiceRepository.update(service, name="住房公积金提取咨询")
    assert service.name_pinyin == "zhu fang gong ji jin ti qu zi xun"


# ------------------------------------------------------------------ 排序行为
def test_sort_by_name_uses_pinyin_not_codepoint(app):
    """强回归：码点序下"住"(U+4F4F) 在"成"(U+6210) 之前，拼音序相反。"""
    db.session.add_all(
        [make_service("住房公积金提取咨询"), make_service("成人职业技能培训报名")]
    )
    db.session.commit()

    names = [s.name for s in ServiceRepository.search(sort="name", per_page=20).items]
    assert names == ["成人职业技能培训报名", "住房公积金提取咨询"]


def test_sort_by_name_orders_she_before_shen(app):
    db.session.add_all(
        [make_service("身份证换领办理"), make_service("社保卡申领"), make_service("社区洗衣干洗")]
    )
    db.session.commit()

    names = [s.name for s in ServiceRepository.search(sort="name", per_page=20).items]
    assert names == ["社保卡申领", "社区洗衣干洗", "身份证换领办理"]


def test_same_pinyin_falls_back_to_id(app):
    """同音不同字（张三/张叁）键完全相同，由二级排序 id 兜底，分页才稳定。"""
    first = make_service("张三服务")
    second = make_service("张叁服务")
    db.session.add_all([first, second])
    db.session.commit()

    assert first.name_pinyin == second.name_pinyin
    items = ServiceRepository.search(sort="name", per_page=20).items
    assert [s.id for s in items] == sorted([first.id, second.id])


# ------------------------------------------------------------------ 视图层
def test_search_page_renders_in_pinyin_order(client, app):
    db.session.add_all(
        [make_service("住房公积金提取咨询"), make_service("成人职业技能培训报名")]
    )
    db.session.commit()

    body = client.get("/services/?sort=name").get_data(as_text=True)
    assert body.index("成人职业技能培训报名") < body.index("住房公积金提取咨询")


def test_sort_option_label_mentions_pinyin(client):
    """下拉文案要自解释，用户不该去猜"按名称"是哪种排法。"""
    body = client.get("/services/").get_data(as_text=True)
    assert "按名称（拼音）" in body
