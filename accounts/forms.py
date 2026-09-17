from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import CustomUser


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


class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "email", "phone", "whatsapp_number", "address", "city", "avatar")
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }