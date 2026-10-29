"""用户管理相关表单：注册、登录、个人信息。

表单层职责：字段级格式校验（WTForms）+ 业务唯一性校验（自定义 validate_xxx）
+ 密码强度（委托 services.password_policy，规则只维护一份）。
"""
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

from app.repositories import UserRepository
from app.services.password_policy import validate_password


class RegistrationForm(FlaskForm):
    username = StringField(
        "用户名",
        validators=[
            DataRequired(message="请输入用户名。"),
            Length(min=3, max=20, message="用户名长度为 3-20 个字符。"),
            Regexp(r"^[A-Za-z0-9_]+$", message="用户名只能包含字母、数字或下划线。"),
        ],
    )
    email = StringField(
        "邮箱", validators=[DataRequired(message="请输入邮箱。"), Email(message="邮箱格式不正确。")]
    )
    phone = StringField(
        "手机号",
        validators=[
            Optional(),
            Length(min=11, max=11, message="手机号需为 11 位。"),
            Regexp(r"^1[3-9]\d{9}$", message="手机号格式不正确。"),
        ],
    )
    real_name = StringField("真实姓名", validators=[Optional(), Length(max=30)])
    password = PasswordField("密码", validators=[DataRequired(message="请输入密码。")])
    confirm = PasswordField(
        "确认密码",
        validators=[DataRequired(message="请再次输入密码。"), EqualTo("password", message="两次输入的密码不一致。")],
    )
    submit = SubmitField("注册")

    def validate_username(self, field):
        if UserRepository.username_exists(field.data):
            raise ValidationError("该用户名已被注册。")

    def validate_email(self, field):
        if UserRepository.email_exists(field.data):
            raise ValidationError("该邮箱已被注册。")

    def validate_password(self, field):
        errors = validate_password(field.data or "", username=self.username.data)
        if errors:
            raise ValidationError("；".join(errors))


class LoginForm(FlaskForm):
    login = StringField("用户名或邮箱", validators=[DataRequired(message="请输入用户名或邮箱。")])
    password = PasswordField("密码", validators=[DataRequired(message="请输入密码。")])
    remember = BooleanField("记住我")
    submit = SubmitField("登录")


class ProfileForm(FlaskForm):
    real_name = StringField("真实姓名", validators=[Optional(), Length(max=30)])
    email = StringField("邮箱", validators=[DataRequired(message="请输入邮箱。"), Email(message="邮箱格式不正确。")])
    phone = StringField(
        "手机号",
        validators=[
            Optional(),
            Length(min=11, max=11, message="手机号需为 11 位。"),
            Regexp(r"^1[3-9]\d{9}$", message="手机号格式不正确。"),
        ],
    )
    submit = SubmitField("保存修改")

    def __init__(self, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        if field.data == self.original_email:
            return
        if UserRepository.email_exists(field.data):
            raise ValidationError("该邮箱已被其它账号使用。")
