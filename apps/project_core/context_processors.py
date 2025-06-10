from django.conf import settings
from django.db import models
from django.utils import timezone
from .models import SystemNotification


def vending_hive_context(request):
    """
    Add Vending Hive specific context variables to all templates.
    """
    context = {
        'VENDING_HIVE': settings.VENDING_HIVE,
        'BRAND_COLORS': settings.VENDING_HIVE['BRAND_COLORS'],
    }
    
    # Add current notifications for logged-in users
    if request.user.is_authenticated:
        current_notifications = SystemNotification.objects.filter(
            is_active=True,
            start_date__lte=timezone.now()
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now())
        )
        context['current_notifications'] = current_notifications
    
    return context