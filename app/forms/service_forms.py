"""服务查询相关表单（GET 表单，用于搜索与排序）。"""
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import Optional

from app.utils.constants import SERVICE_CATEGORIES, SORT_OPTIONS


class ServiceSearchForm(FlaskForm):
    keyword = StringField("关键词", validators=[Optional()])
    category = SelectField(
        "分类",
        choices=[("", "全部分类")] + list(SERVICE_CATEGORIES.items()),
        validators=[Optional()],
    )
    sort = SelectField("排序", choices=list(SORT_OPTIONS.items()), default="default")
    submit = SubmitField("搜索")


class AnnouncementSearchForm(FlaskForm):
    keyword = StringField("关键词", validators=[Optional()])
    submit = SubmitField("搜索")
