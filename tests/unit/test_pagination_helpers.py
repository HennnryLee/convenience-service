"""分页与枚举参数解析测试（等价类 + 边界值）。"""
from app.utils.pagination import parse_choice, parse_page


def test_parse_page_accepts_positive_integers():
    assert parse_page("1") == 1
    assert parse_page(2) == 2
    assert parse_page("999") == 999


def test_parse_page_clamps_zero_and_negative_to_one():
    assert parse_page("0") == 1
    assert parse_page(-5) == 1
    assert parse_page("-1") == 1


def test_parse_page_falls_back_on_garbage():
    assert parse_page(None) == 1
    assert parse_page("") == 1
    assert parse_page("abc") == 1
    assert parse_page("1.5") == 1
    assert parse_page(object()) == 1


def test_parse_page_uses_custom_default():
    assert parse_page("abc", default=3) == 3


def test_parse_choice_whitelist():
    allowed = {"pending", "confirmed"}
    assert parse_choice("pending", allowed) == "pending"
    assert parse_choice("cancelled", allowed) is None
    assert parse_choice("", allowed) is None
    assert parse_choice(None, allowed) is None
    assert parse_choice("other", allowed, default="pending") == "pending"


def test_parse_choice_accepts_any_iterable():
    assert parse_choice("a", ["a", "b"]) == "a"
    assert parse_choice("c", ("a", "b")) is None


def test_validate_keyword_boundaries():
    from app.utils.validators import validate_keyword

    assert validate_keyword(None) == ""
    assert validate_keyword("  身份证  ") == "身份证"
    assert validate_keyword("a" * 50, max_length=50) == "a" * 50
    assert validate_keyword("a" * 51, max_length=50) is None

