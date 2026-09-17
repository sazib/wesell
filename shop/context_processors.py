from django.db.models import Count

from .models import Category

def categories_processor(request):
    categories = Category.objects.filter(is_active=True).annotate(product_count=Count("products"))
    return {"nav_categories": categories}