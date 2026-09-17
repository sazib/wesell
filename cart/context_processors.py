from cart.models import Cart


def cart_count_processor(request):
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            count = cart.total_items
    elif request.session.session_key:
        key = request.session.session_key
        cart = Cart.objects.filter(session_key=key).first()
        if cart:
            count = cart.total_items
    return {"cart_count": count}