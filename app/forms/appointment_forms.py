"""在线预约相关表单。"""
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from app.utils.constants import TIME_SLOTS


class AppointmentForm(FlaskForm):
    appointment_date = DateField(
        "预约日期", format="%Y-%m-%d", validators=[DataRequired(message="请选择预约日期。")]
    )
    time_slot = SelectField(
        "预约时段",
        choices=[(slot, slot) for slot in TIME_SLOTS],
        validators=[DataRequired(message="请选择预约时段。")],
    )
    contact_name = StringField(
        "联系人姓名",
        validators=[DataRequired(message="请填写联系人姓名。"), Length(min=2, max=30)],
    )
    contact_phone = StringField(
        "联系电话",
        validators=[
            DataRequired(message="请填写联系电话。"),
            Length(min=11, max=11, message="联系电话需为 11 位。"),
            Regexp(r"^1[3-9]\d{9}$", message="手机号格式不正确。"),
        ],
    )
    remark = TextAreaField("备注", validators=[Optional(), Length(max=200)])
    submit = SubmitField("提交预约")


class AppointmentSearchForm(FlaskForm):
    status = SelectField(
        "状态",
        choices=[("", "全部"), ("pending", "待确认"), ("confirmed", "已确认"),
                 ("completed", "已完成"), ("cancelled", "已取消")],
        validators=[Optional()],
    )
    submit = SubmitField("筛选")
