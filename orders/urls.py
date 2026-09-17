from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("orders/", views.order_list, name="list"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/address/", views.shipping_address, name="address"),
    path("checkout/confirmation/", views.confirmation, name="confirmation"),
    path("custom-cake/", views.custom_cake, name="custom_cake"),
    path("order/<str:order_number>/", views.order_detail, name="detail"),
    path("order/<str:order_number>/cancel/", views.cancel_order, name="cancel"),
    path("order/<str:order_number>/payment/confirm/", views.confirm_payment, name="confirm_payment"),
    path("success/<str:order_number>/", views.order_success, name="success"),
]