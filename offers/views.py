from decimal import Decimal, ROUND_HALF_UP

from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import CountdownOffer


def offer_list(request):
    offers = CountdownOffer.objects.filter(is_active=True)
    now = timezone.now()
    running = [o for o in offers if o.is_running]
    upcoming = [o for o in offers if not o.is_running and o.starts_at > now]
    context = {
        "running_offers": running,
        "upcoming_offers": upcoming,
    }
    return render(request, "offers/list.html", context)


def offer_detail(request, slug):
    offer = get_object_or_404(CountdownOffer, slug=slug, is_active=True)
    products = list(offer.products.filter(is_available=True))
    for product in products:
        if product.sale_price:
            product.offer_price = product.sale_price
        else:
            product.offer_price = (
                product.base_price * offer.discount_multiplier
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    context = {"offer": offer, "products": products}
    return render(request, "offers/detail.html", context)