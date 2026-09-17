from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from orders.models import Order
from shop.models import Product

from .forms import ReviewForm
from .models import Review


@login_required
@require_POST
def add_review(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review, created = Review.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                "rating": form.cleaned_data["rating"],
                "title": form.cleaned_data["title"],
                "comment": form.cleaned_data["comment"],
            },
        )
        messages.success(request, "Thank you! Your review was published.")
    else:
        messages.error(request, "Please enter a rating and your feedback.")
    return redirect(product.get_absolute_url())