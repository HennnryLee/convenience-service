"""实体层数据规范化测试（写入钩子）。

验证"规范化发生在实体层"这一设计：无论从表单、seed、CLI 还是测试造数进入，
邮箱大小写、用户名/服务名首尾空白都不会产生重复账号/重复服务或错误排序键。
"""
from app.extensions import db
from app.models import ServiceItem, User
from app.repositories import ServiceRepository, UserRepository


def test_email_is_lowercased_on_write(app):
    user = User(username="MixedCase", email="Foo.Bar@Example.COM", role="user")
    user.set_password("User@123")
    db.session.add(user)
    db.session.commit()

    assert user.email == "foo.bar@example.com"
    assert UserRepository.get_by_email("FOO.BAR@example.com").id == user.id
    assert UserRepository.get_by_login("Foo.Bar@Example.com").id == user.id


def test_username_is_stripped_on_write(app):
    user = User(username="  spacey  ", email="spacey@example.com", role="user")
    user.set_password("User@123")
    db.session.add(user)
    db.session.commit()

    assert user.username == "spacey"
    assert UserRepository.get_by_username("spacey").id == user.id


def test_service_name_is_stripped_and_pinyin_key_follows(app):
    service = ServiceItem(name="  重庆小面  ", category="life", price=10, daily_capacity=2)
    db.session.add(service)
    db.session.commit()

    assert service.name == "重庆小面"
    assert service.name_pinyin == "chong qing xiao mian"
    assert ServiceRepository.get_by_name("重庆小面").id == service.id


def test_service_name_conflict_excludes_self(app, service_factory):
    first = service_factory(name="重名服务")
    second = service_factory(name="另一个服务")

    assert ServiceRepository.name_conflict("重名服务") is True
    assert ServiceRepository.name_conflict("重名服务", exclude_id=first.id) is False
    assert ServiceRepository.name_conflict("不存在") is False
    assert second.id is not None


def test_service_average_rating_property(
    app, user_factory, service_factory, appointment_factory
):
    """实体属性：无评价返回 None（避免把"0 分"展示给用户），有评价取平均。"""
    from app.models import Feedback

    user = user_factory()
    service = service_factory(name="属性评分服务")
    assert service.average_rating is None

    for index, rating in enumerate((2, 4), start=1):
        appt = appointment_factory(
            user, service, status="completed", slot=f"{8 + index}:00-{9 + index}:00"
        )
        db.session.add(Feedback(
            user_id=user.id, service_id=service.id, appointment_id=appt.id, rating=rating
        ))
    db.session.commit()
    db.session.refresh(service)
    assert service.average_rating == 3.0


def test_user_password_hash_never_stores_plaintext(app):
    user = User(username="hashcheck", email="hash@example.com", role="user")
    user.set_password("User@123")
    assert user.password_hash and "User@123" not in user.password_hash
    assert user.check_password("User@123") is True
    assert user.check_password("wrong") is False

