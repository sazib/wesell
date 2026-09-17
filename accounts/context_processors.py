from django.conf import settings

from offers.models import CountdownOffer


def site_settings(request):
    running_offer = CountdownOffer.objects.filter(is_active=True).order_by("-ends_at").first()
    running_offer = running_offer if running_offer and running_offer.is_running else None
    return {
        "whatsapp_number": settings.WHATSAPP_NUMBER,
        "messenger_url": settings.MESSENGER_PAGE_URL,
        "running_offer": running_offer,
    }