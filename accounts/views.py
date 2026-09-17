from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from cart.views import get_or_create_cart
from shop.models import Category

from .forms import CustomUserCreationForm, ProfileForm


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