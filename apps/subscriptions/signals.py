from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import LeadCreditPackage, PaymentHistory
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LeadCreditPackage)
@receiver(post_delete, sender=LeadCreditPackage)
def clear_package_cache(sender, **kwargs):
    """Clear package-related cache when packages are modified."""
    cache_keys = [
        'active_packages',
        'packages_by_plan'
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    logger.info("Package cache cleared")


@receiver(post_save, sender=PaymentHistory)
def handle_payment_status_change(sender, instance, **kwargs):
    """Handle payment status changes."""
    if instance.status == 'completed':
        logger.info(f"Payment completed: {instance.transaction_id} - ${instance.amount}")
    elif instance.status == 'failed':
        logger.warning(f"Payment failed: {instance.transaction_id} - {instance.failure_reason}")