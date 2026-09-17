from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from shop.models import Product

from .forms import AddToCartForm, UpdateCartItemForm
from .models import Cart, CartItem


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        if request.session.get("cart_key"):
            old_cart = Cart.objects.filter(session_key=request.session["cart_key"]).exclude(pk=cart.pk).first()
            if old_cart:
                cart.merge_session_to_user(request.user)
        return cart
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key
    cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def cart_detail(request):
    cart = get_or_create_cart(request)
    items = cart.get_items()
    subtotal = cart.subtotal
    context = {"cart": cart, "items": items, "subtotal": subtotal}
    return render(request, "cart/detail.html", context)


@require_POST
def add_to_cart(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug, is_available=True)
    form = AddToCartForm(request.POST, product=product)
    if not form.is_valid():
        messages.error(request, "Could not add item to cart. Please check the selected options.")
        return redirect(product.get_absolute_url())

    cart = get_or_create_cart(request)
    data = form.cleaned_data
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        size=data.get("size", ""),
        flavor=data.get("flavor", ""),
        defaults={"quantity": data["quantity"], "unit_price": product.current_price},
    )
    if not created:
        item.quantity += data["quantity"]
        item.save()
    messages.success(request, f"{product.name} added to cart.")
    return HttpResponseRedirect(reverse("cart:detail"))


@require_POST
def update_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id)
    form = UpdateCartItemForm(request.POST)
    if form.is_valid():
        item.quantity = form.cleaned_data["quantity"]
        item.save()
    return redirect("cart:detail")


@require_POST
def remove_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id)
    item.delete()
    messages.info(request, "Item removed from cart.")
    return redirect("cart:detail")


@require_POST
def clear_cart(request):
    cart = get_or_create_cart(request)
    cart.items.all().delete()
    messages.info(request, "Cart cleared.")
    return redirect("cart:detail")


def cart_count(request):
    cart = get_or_create_cart(request)
    return JsonResponse({"count": cart.total_items})