from django.urls import path
from django.contrib.auth.views import LogoutView

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("password-reset/", views.forgot_password, name="forgot_password"),
    path("password-reset/verify/", views.verify_otp, name="verify_otp"),
    path("password-reset/confirm/", views.reset_password, name="reset_password"),
]