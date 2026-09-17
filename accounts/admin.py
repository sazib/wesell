from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "phone", "city", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Bakery Profile", {"fields": ("phone", "address", "city", "whatsapp_number", "avatar")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Bakery Profile", {"fields": ("phone", "address", "city", "whatsapp_number")}),
    )