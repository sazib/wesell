from decimal import Decimal, ROUND_HALF_UP

import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from cart.views import get_or_create_cart
from offers.models import CountdownOffer
from shop.models import DeliveryArea

from .forms import CheckoutForm, CustomCakeForm, ShippingAddressForm
from .models import Order, OrderItem
from .payments import create_payment, verify_payment

CUSTOM_CAKE_BASE = Decimal("500.00")
CUSTOM_CAKE_SIZE_EXTRA = {
    "half_kg": Decimal("100.00"),
    "one_kg": Decimal("500.00"),
    "two_kg": Decimal("1300.00"),
    "small": Decimal("200.00"),
    "medium": Decimal("450.00"),
    "large": Decimal("800.00"),
}
CUSTOM_CAKE_FLAVOR_EXTRA = {
    "red_velvet": Decimal("300.00"),
    "butterscotch": Decimal("250.00"),
    "mango": Decimal("200.00"),
    "eggless_chocolate": Decimal("150.00"),
    "eggless_vanilla": Decimal("150.00"),
}
CUSTOM_CAKE_FILLING_EXTRA = {
    "chocolate_ganache": Decimal("150.00"),
    "cheese": Decimal("200.00"),
    "fruit": Decimal("100.00"),
}

CHECKOUT_SESSION_KEY = "checkout_payload"


def _money(value):
    """Normalise a Decimal to two decimal places for display/storage."""
    return (value or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _running_offer():
    offer = CountdownOffer.objects.filter(is_active=True).order_by("-ends_at").first()
    return offer if offer and offer.is_running else None


def _profile_initial(user):
    return {
        "full_name": user.get_full_name() or user.username,
        "phone": user.phone,
        "email": user.email,
        "address": user.address,
        "city": user.city,
    }


def _save_profile_address(user, data):
    """Persist the shipping details onto the user's profile."""
    full_name = (data.get("full_name") or "").strip()
    if full_name:
        parts = full_name.split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
    user.phone = data.get("phone") or ""
    user.address = data.get("address") or ""
    user.city = data.get("city") or ""
    user.save(update_fields=["first_name", "last_name", "phone", "address", "city"])


def _store_checkout_payload(request, data):
    request.session[CHECKOUT_SESSION_KEY] = {
        "full_name": data["full_name"],
        "phone": data["phone"],
        "email": data.get("email", ""),
        "address": data["address"],
        "city": data["city"],
        "grid_coords": data.get("grid_coords", ""),
        "delivery_area_id": data["delivery_area"].id if data.get("delivery_area") else None,
        "delivery_date": str(data["delivery_date"]),
        "delivery_time_slot": data.get("delivery_time_slot", ""),
        "notes": data.get("notes", ""),
    }
    request.session.modified = True


def _load_checkout_payload(request):
    return request.session.get(CHECKOUT_SESSION_KEY)


def _clear_checkout_payload(request):
    request.session.pop(CHECKOUT_SESSION_KEY, None)
    request.session.modified = True


def checkout(request):
    cart = get_or_create_cart(request)
    if cart.is_empty:
        messages.info(request, "Your cart is empty. Add some treats first.")
        return redirect("cart:detail")

    # Logged-in users without a saved shipping address must add one first.
    if request.method == "GET" and request.user.is_authenticated and not request.user.address:
        messages.info(request, "Please add a shipping address to continue.")
        return redirect("orders:address")

    running_offer = _running_offer()

    initial = {}
    if request.user.is_authenticated:
        initial = _profile_initial(request.user)
    payload = _load_checkout_payload(request)
    if payload:
        initial = {**initial, **payload}

    form = CheckoutForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if request.user.is_authenticated:
            _save_profile_address(request.user, data)
        _store_checkout_payload(request, data)
        messages.success(request, "Almost there — please review your order and confirm.")
        return redirect("orders:confirmation")

    delivery_area = None
    if payload and payload.get("delivery_area_id"):
        delivery_area = DeliveryArea.objects.filter(pk=payload["delivery_area_id"]).first()
    delivery_fee = delivery_area.delivery_fee if delivery_area else Decimal("0")

    discount = sum(
        (item.unit_price * (Decimal(running_offer.discount_percent) / Decimal("100")) * item.quantity)
        for item in cart.get_items()
    ) if running_offer else Decimal("0")

    context = {
        "cart": cart,
        "form": form,
        "running_offer": running_offer,
        "discount": _money(discount),
        "delivery_fee": _money(delivery_fee),
        "total": _money(cart.subtotal - discount + delivery_fee),
        "delivery_areas": {
            str(area.id): str(area.delivery_fee)
            for area in DeliveryArea.objects.filter(is_active=True)
        },
    }
    if request.method == "POST":
        # Re-render with validation errors so the user can fix the form.
        messages.error(request, "Please fix the highlighted fields and try again.")
    return render(request, "orders/checkout.html", context)


def shipping_address(request):
    """Shipping Address screen shown to logged-in users with no saved address."""
    if not request.user.is_authenticated:
        return redirect("orders:checkout")
    if request.user.address:
        return redirect("orders:checkout")

    cart = get_or_create_cart(request)
    if cart.is_empty:
        return redirect("cart:detail")

    form = ShippingAddressForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Shipping address saved. You can now complete your checkout.")
        return redirect("orders:checkout")

    context = {"form": form, "cart": cart}
    return render(request, "orders/address.html", context)


def _order_totals(cart, payload, running_offer):
    delivery_area = None
    if payload.get("delivery_area_id"):
        delivery_area = DeliveryArea.objects.filter(pk=payload["delivery_area_id"]).first()
    delivery_fee = delivery_area.delivery_fee if delivery_area else Decimal("0")
    discount = sum(
        (item.unit_price * (Decimal(running_offer.discount_percent) / Decimal("100")) * item.quantity)
        for item in cart.get_items()
    ) if running_offer else Decimal("0")
    subtotal = cart.subtotal
    total = subtotal - discount + delivery_fee
    return (delivery_area, _money(delivery_fee), _money(discount), _money(subtotal), _money(total))


def _parse_delivery_date(payload):
    value = payload.get("delivery_date")
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def confirmation(request):
    """Order Confirmation page: review order details before final payment."""
    cart = get_or_create_cart(request)
    if cart.is_empty:
        messages.info(request, "Your cart is empty.")
        return redirect("cart:detail")

    payload = _load_checkout_payload(request)
    if not payload:
        messages.info(request, "Please complete your checkout details first.")
        return redirect("orders:checkout")

    running_offer = _running_offer()
    delivery_area, delivery_fee, discount, subtotal, total = _order_totals(cart, payload, running_offer)

    if request.method == "POST":
        return _create_order_and_pay(request, cart, payload, running_offer)

    context = {
        "cart": cart,
        "payload": payload,
        "delivery_date": _parse_delivery_date(payload),
        "delivery_area": delivery_area,
        "delivery_fee": delivery_fee,
        "discount": discount,
        "subtotal": subtotal,
        "total": total,
        "running_offer": running_offer,
    }
    return render(request, "orders/confirmation.html", context)


@require_POST
def _create_order_and_pay(request, cart, payload, running_offer):
    """Create the order from the stored checkout payload, charge, and clean up."""
    if cart.is_empty:
        messages.warning(request, "Your cart has changed. Please review it before ordering.")
        return redirect("cart:detail")

    delivery_area, delivery_fee, _, _, _ = _order_totals(cart, payload, running_offer)

    with transaction.atomic():
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=payload["full_name"],
            phone=payload["phone"],
            email=payload.get("email", ""),
            address=payload["address"],
            city=payload["city"],
            grid_coords=payload.get("grid_coords", ""),
            delivery_area=delivery_area,
            delivery_fee=delivery_fee,
            delivery_date=_parse_delivery_date(payload),
            delivery_time_slot=payload.get("delivery_time_slot", ""),
            notes=payload.get("notes", ""),
        )
        discount_total = Decimal("0")
        for item in cart.get_items():
            unit_discount = Decimal("0")
            if running_offer and item.product in running_offer.products.all():
                unit_discount = item.unit_price * (Decimal(running_offer.discount_percent) / Decimal("100"))
            line_discount = unit_discount * item.quantity
            discount_total += line_discount
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                size=item.size,
                flavor=item.flavor,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=line_discount,
            )
        order.discount = discount_total
        order.recalculate_totals()

        payment = create_payment(order)
        if payment["success"] and payment["gateway"] == "sandbox":
            order.payment_status = Order.PaymentStatus.PAID
            order.payment_reference = payment["reference"]
            order.payment_gateway = payment["gateway"]
            order.save()
            cart.items.all().delete()
            _clear_checkout_payload(request)
            messages.success(request, "Payment successful! Your order is confirmed.")
            return redirect("orders:success", order_number=order.order_number)

        if payment["success"]:
            order.payment_reference = payment["reference"]
            order.payment_gateway = payment["gateway"]
            order.save()
            _clear_checkout_payload(request)
            if payment.get("redirect_url"):
                return redirect(payment["redirect_url"])
            return redirect("orders:success", order_number=order.order_number)

        messages.error(request, f"Payment failed: {payment.get('error', 'Unknown error')}")
        order.status = Order.Status.CANCELLED
        order.save()
        _clear_checkout_payload(request)
        return redirect("orders:detail", order_number=order.order_number)


def custom_cake(request):
    form = CustomCakeForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        price = CUSTOM_CAKE_BASE
        price += CUSTOM_CAKE_SIZE_EXTRA.get(data["size"], Decimal("0"))
        price += CUSTOM_CAKE_FLAVOR_EXTRA.get(data["flavor"], Decimal("0"))
        price += CUSTOM_CAKE_FILLING_EXTRA.get(data.get("filling", ""), Decimal("0"))

        notes = data["notes"]

        photo_name = ""
        if data.get("reference_photo"):
            photo_name = data["reference_photo"].name

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=request.user.get_full_name() if request.user.is_authenticated else "Custom Cake Customer",
            phone=request.user.phone if request.user.is_authenticated else "",
            email=request.user.email if request.user.is_authenticated else "",
            address=request.user.address if request.user.is_authenticated else "",
            city=request.user.city if request.user.is_authenticated else "",
            notes=notes,
            delivery_date=None,
            subtotal=price * data["quantity"],
            total=price * data["quantity"],
            is_custom_order=True,
            custom_cake={
                "occasion": data["occasion"],
                "theme": data["theme"],
                "size": data["size"],
                "flavor": data["flavor"],
                "filling": data.get("filling", ""),
                "quantity": data["quantity"],
                "reference_photo": photo_name,
            },
            payment_status=Order.PaymentStatus.UNPAID,
        )

        messages.success(
            request,
            "Your custom cake request was received! We will contact you shortly to confirm details and payment.",
        )
        return redirect("orders:detail", order_number=order.order_number)

    context = {"form": form, "base_price": CUSTOM_CAKE_BASE, "size_extras": CUSTOM_CAKE_SIZE_EXTRA}
    return render(request, "orders/custom_cake.html", context)


def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if order.user and request.user.is_authenticated and order.user != request.user:
        messages.error(request, "You are not allowed to view that order.")
        return redirect("orders:list")
    context = {"order": order}
    return render(request, "orders/detail.html", context)


def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if request.user.is_authenticated and order.user and order.user != request.user:
        return redirect("orders:list")
    context = {"order": order}
    return render(request, "orders/success.html", context)


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user)
    active = orders.exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED])
    past = orders.filter(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED])
    context = {"active": active, "past": past}
    return render(request, "orders/list.html", context)


@require_POST
@login_required
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status == Order.Status.PENDING:
        order.status = Order.Status.CANCELLED
        order.save()
        messages.success(request, "Order cancelled.")
    else:
        messages.error(request, "This order cannot be cancelled at this stage.")
    return redirect("orders:detail", order_number=order.order_number)


@require_POST
def confirm_payment(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    verified = verify_payment(order)
    if verified and order.payment_status != Order.PaymentStatus.PAID:
        order.payment_status = Order.PaymentStatus.PAID
        order.save()
        _send_confirmation(order)
        messages.success(request, "Payment confirmed.")
    else:
        messages.error(request, "Could not verify payment.")
    return redirect("orders:detail", order_number=order.order_number)


def _send_confirmation(order):
    try:
        if order.email:
            send_mail(
                subject=f"Order {order.order_number} confirmed",
                message=(
                    f"Hi {order.full_name},\n\n"
                    f"Your order {order.order_number} has been received.\n"
                    f"Total: {order.total}\n"
                    f"Expected delivery: {order.delivery_date}\n\n"
                    f"Thank you for ordering with us!"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                fail_silently=True,
            )
    except TypeError:
        pass