from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from offers.models import CountdownOffer
from reviews.models import Review

from .models import Category, Product


def home(request):
    featured = Product.objects.filter(is_available=True, is_featured=True).select_related("category")[:8]
    categories = Category.objects.filter(is_active=True)
    newest = Product.objects.filter(is_available=True).select_related("category").order_by("-created")[:8]
    running_offer = CountdownOffer.objects.filter(is_active=True).order_by("-ends_at").first()
    running_offer = running_offer if running_offer and running_offer.is_running else None
    offer_products = list(running_offer.products.filter(is_available=True)) if running_offer else []
    context = {
        "featured": featured,
        "categories": categories,
        "newest": newest,
        "running_offer": running_offer,
        "offer_products": offer_products,
    }
    return render(request, "shop/home.html", context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = category.products.filter(is_available=True)
    sort = request.GET.get("sort", "newest")
    if sort == "price_asc":
        products = products.order_by("base_price")
    elif sort == "price_desc":
        products = products.order_by("-base_price")
    elif sort == "rating":
        products = products.annotate(avg_rating=Avg("reviews__rating")).order_by("-avg_rating")
    else:
        products = products.order_by("-created")
    context = {"category": category, "products": products, "sort": sort}
    return render(request, "shop/category_detail.html", context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    reviews = Review.objects.filter(product=product, is_published=True).select_related("user")
    avg_rating = reviews.aggregate(avg=Avg("rating"), count=Count("id"))
    related = (
        Product.objects.filter(category=product.category, is_available=True)
        .exclude(pk=product.pk)
        .select_related("category")[:4]
    )
    context = {
        "product": product,
        "reviews": reviews,
        "avg_rating": avg_rating["avg"] or 0,
        "review_count": avg_rating["count"],
        "related": related,
    }
    return render(request, "shop/product_detail.html", context)


@require_GET
def search(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.none()
    if query:
        products = (
            Product.objects.filter(is_available=True)
            .filter(Q(name__icontains=query) | Q(description__icontains=query))
            .select_related("category")
        )
    context = {"query": query, "products": products}
    return render(request, "shop/search.html", context)