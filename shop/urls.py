from django.urls import path

from . import views
from .views import home, category_detail, product_detail, search

app_name = "shop"

urlpatterns = [
    path("", home, name="home"),
    path("shop/", search, name="search"),
    path("category/<slug:slug>/", category_detail, name="category_detail"),
    path("product/<slug:slug>/", product_detail, name="product_detail"),
]