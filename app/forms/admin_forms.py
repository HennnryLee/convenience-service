"""后台管理相关表单：服务维护、公告发布、预约状态处理。"""
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from app.services.password_policy import validate_password
from app.utils.constants import APPOINTMENT_STATUS_TEXT, SERVICE_CATEGORIES


class ServiceForm(FlaskForm):
    name = StringField(
        "服务名称",
        validators=[DataRequired(message="请填写服务名称。"), Length(max=100)],
        render_kw={"autocomplete": "off"},
    )
    category = SelectField(
        "服务分类", choices=list(SERVICE_CATEGORIES.items()), validators=[DataRequired()]
    )
    description = TextAreaField("服务简介", validators=[Optional(), Length(max=500)])
    address = StringField("办理地点", validators=[Optional(), Length(max=200)])
    price = DecimalField(
        "服务费用（元）", default=0,
        validators=[NumberRange(min=0, message="费用不能为负数。")],
        render_kw={"inputmode": "decimal"},
    )
    duration_minutes = IntegerField(
        "预计耗时（分钟）", default=30,
        validators=[NumberRange(min=1)],
        render_kw={"inputmode": "numeric"},
    )
    daily_capacity = IntegerField(
        "每时段可预约人数", default=5,
        validators=[NumberRange(min=1, message="容量至少为 1。")],
        render_kw={"inputmode": "numeric"},
    )
    status = SelectField("上架状态", choices=[("online", "上架"), ("offline", "下架")])
    submit = SubmitField("保存")


class AnnouncementForm(FlaskForm):
    title = StringField("公告标题", validators=[DataRequired(message="请填写标题。"), Length(max=100)])
    content = TextAreaField("公告正文", validators=[DataRequired(message="请填写正文。")])
    is_published = BooleanField("立即发布", default=True)
    submit = SubmitField("发布公告")


class AppointmentStatusForm(FlaskForm):
    status = SelectField(
        "目标状态", choices=list(APPOINTMENT_STATUS_TEXT.items()), validators=[DataRequired()]
    )
    submit = SubmitField("更新状态")


class UserSearchForm(FlaskForm):
    keyword = StringField("关键词", validators=[Optional()])
    submit = SubmitField("搜索")


class AdminResetPasswordForm(FlaskForm):
    """管理员为普通用户设置临时密码。

    管理员永远看不到原密码；只输入新密码两次。密码规则复用用户注册时的
    validate_password（长度、字母+数字、空格、不能与用户名相同）。
    """

    password = PasswordField(
        "临时密码",
        validators=[DataRequired(message="请输入临时密码。")],
        render_kw={"autocomplete": "new-password"},
    )
    confirm = PasswordField(
        "确认临时密码",
        validators=[
            DataRequired(message="请再次输入临时密码。"),
            EqualTo("password", message="两次输入的密码不一致。"),
        ],
        render_kw={"autocomplete": "new-password"},
    )
    submit = SubmitField("确认重置")

    def __init__(self, target_username=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_username = target_username

    def validate_password(self, field):
        errors = validate_password(field.data or "", username=self.target_username)
        if errors:
            raise ValidationError("；".join(errors))
