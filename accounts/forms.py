import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.contrib.auth.hashers import check_password

from .models import CustomUser, PasswordHistory


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"placeholder": "First name"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"placeholder": "Last name"}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={"placeholder": "Phone number"}))
    whatsapp_number = forms.CharField(
        max_length=20, required=False, widget=forms.TextInput(attrs={"placeholder": "WhatsApp number"})
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email", "first_name", "last_name", "phone", "whatsapp_number")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            PasswordHistory.objects.create(user=user, password_hash=user.password)
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone", "whatsapp_number", "address", "city", "avatar")
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or username",
        max_length=254,
        widget=forms.TextInput(
            attrs={"autofocus": True, "autocomplete": "username", "placeholder": "you@example.com"}
        ),
    )


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("No account is registered with this email address.")
        return email


class VerifyOTPForm(forms.Form):
    otp = forms.CharField(
        label="One-Time Password",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "placeholder": "6-digit code",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "pattern": "[0-9]{6}",
            }
        ),
    )


class SetNewPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password1(self):
        password1 = self.cleaned_data.get("new_password1")
        if not password1:
            return password1
        if len(password1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        missing = []
        if not re.search(r"[a-z]", password1):
            missing.append("a lowercase letter")
        if not re.search(r"[A-Z]", password1):
            missing.append("an uppercase letter")
        if not re.search(r"\d", password1):
            missing.append("a number")
        if not re.search(r"[^A-Za-z0-9]", password1):
            missing.append("a special character")
        if missing:
            raise forms.ValidationError(f"Password must contain {', '.join(missing)}.")
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "The two password fields didn't match.")
        if password1 and self.user and (
            check_password(password1, self.user.password)
            or any(
                check_password(password1, hash)
                for hash in self.user.password_history.order_by("-created_at", "-id")[:3].values_list(
                    "password_hash", flat=True
                )
            )
        ):
            raise forms.ValidationError(
                "Your new password can't be the same as your current password or any of your previous 3 passwords."
            )
        return cleaned_data