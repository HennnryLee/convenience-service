"""表单包：按模块组织，统一由 Flask-WTF 提供 CSRF 防护。"""
from .admin_forms import AnnouncementForm, AppointmentStatusForm, ServiceForm, UserSearchForm
from .appointment_forms import AppointmentForm, AppointmentSearchForm
from .auth_forms import LoginForm, ProfileForm, RegistrationForm
from .feedback_forms import FeedbackForm
from .service_forms import AnnouncementSearchForm, ServiceSearchForm

__all__ = [
    "RegistrationForm",
    "LoginForm",
    "ProfileForm",
    "ServiceSearchForm",
    "AnnouncementSearchForm",
    "AppointmentForm",
    "AppointmentSearchForm",
    "FeedbackForm",
    "ServiceForm",
    "AnnouncementForm",
    "AppointmentStatusForm",
    "UserSearchForm",
]
