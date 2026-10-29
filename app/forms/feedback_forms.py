"""反馈评价相关表单。"""
from flask_wtf import FlaskForm
from wtforms import RadioField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.utils.constants import RATING_TEXT


class FeedbackForm(FlaskForm):
    appointment_id = SelectField("选择已完成的服务", coerce=int, validators=[DataRequired(message="请选择要评价的预约。")])
    rating = RadioField(
        "服务评分",
        coerce=int,
        choices=[(i, f"{i} 星 · {RATING_TEXT[i]}") for i in range(1, 6)],
        validators=[DataRequired(message="请选择评分。")],
    )
    content = TextAreaField("评价内容", validators=[Optional(), Length(max=300)])
    submit = SubmitField("提交评价")
