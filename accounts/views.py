import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from cart.views import get_or_create_cart
from shop.models import Category

from .forms import (
    CustomUserCreationForm,
    EmailAuthenticationForm,
    ForgotPasswordForm,
    ProfileForm,
    SetNewPasswordForm,
    VerifyOTPForm,
)
from .models import CustomUser, PasswordResetToken

OTP_EXPIRY_MINUTES = 15
RESET_EMAIL_SESSION_KEY = "password_reset_email"
RESET_USER_SESSION_KEY = "password_reset_user_id"


def register(request):
    if request.user.is_authenticated:
        return redirect("shop:home")
    form = CustomUserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        cart = get_or_create_cart(request)
        cart.user = user
        cart.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.get_full_name() or user.username}! Your account was created.")
        return redirect("shop:home")
    context = {"form": form}
    return render(request, "accounts/register.html", context)


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    form_class = EmailAuthenticationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        get_or_create_cart(self.request)
        messages.success(self.request, f"Welcome back, {self.request.user.username}!")
        return response


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    context = {"form": form}
    return render(request, "accounts/profile.html", context)


@login_required
def dashboard(request):
    orders = request.user.orders.order_by("-created")[:5]
    context = {"orders": orders}
    return render(request, "accounts/dashboard.html", context)


def _send_otp_email(user, otp):
    subject = "Your Sweet Treats Bakery password reset code"
    message = (
        f"Hi {user.get_full_name() or user.username},\n\n"
        f"Use the following code to reset your password:\n\n{otp}\n\n"
        f"This code expires in {OTP_EXPIRY_MINUTES} minutes. "
        "If you didn't request a password reset, you can safely ignore this email.\n\n"
        "- Sweet Treats Bakery"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def forgot_password(request):
    if request.user.is_authenticated:
        return redirect("shop:home")
    form = ForgotPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = CustomUser.objects.get(email__iexact=email)
        user.reset_tokens.filter(is_used=False).delete()
        otp = f"{secrets.randbelow(1_000_000):06d}"
        PasswordResetToken.objects.create(
            user=user,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        )
        _send_otp_email(user, otp)
        request.session[RESET_EMAIL_SESSION_KEY] = email
        messages.success(
            request,
            f"We emailed a verification code to {email}. It expires in {OTP_EXPIRY_MINUTES} minutes.",
        )
        return redirect("accounts:verify_otp")
    return render(request, "accounts/forgot_password.html", {"form": form})


def verify_otp(request):
    if request.user.is_authenticated:
        return redirect("shop:home")
    email = request.session.get(RESET_EMAIL_SESSION_KEY, "")
    form = VerifyOTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        otp = form.cleaned_data["otp"]
        if not email:
            messages.error(request, "Your reset session expired. Please request a new code.")
            return redirect("accounts:forgot_password")
        try:
            user = CustomUser.objects.get(email__iexact=email)
            token = PasswordResetToken.objects.filter(user=user, is_used=False).latest("created_at")
        except (CustomUser.DoesNotExist, PasswordResetToken.DoesNotExist):
            user = None
            token = None
        if token is None or token.otp != otp or token.is_expired():
            form.add_error("otp", "Invalid or expired code. Please try again.")
        else:
            token.is_used = True
            token.save()
            request.session[RESET_USER_SESSION_KEY] = user.pk
            messages.success(request, "Code verified. Now set a new password.")
            return redirect("accounts:reset_password")
    return render(request, "accounts/verify_otp.html", {"form": form, "email": email})


def reset_password(request):
    if request.user.is_authenticated:
        return redirect("shop:home")
    user_id = request.session.get(RESET_USER_SESSION_KEY)
    if not user_id:
        messages.warning(request, "Please verify your code first.")
        return redirect("accounts:forgot_password")
    user = CustomUser.objects.filter(pk=user_id).first()
    form = SetNewPasswordForm(request.POST or None, user=user)
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["new_password1"])
        user.save()
        user.reset_tokens.all().delete()
        request.session.pop(RESET_USER_SESSION_KEY, None)
        request.session.pop(RESET_EMAIL_SESSION_KEY, None)
        messages.success(request, "Password updated! You can now log in with your new password.")
        return redirect("accounts:login")
    return render(request, "accounts/reset_password.html", {"form": form})