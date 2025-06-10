from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import SearchHistory, LocationData
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SearchHistory)
def handle_search_created(sender, instance, created, **kwargs):
    """Handle actions when a search is created."""
    if created:
        logger.info(f"New search created: {instance.search_summary} by {instance.user.email}")


@receiver(post_save, sender=LocationData)
def handle_location_created(sender, instance, created, **kwargs):
    """Handle actions when location data is created."""
    if created:
        # Clear any cached data related to this user's searches
        cache_key = f"user_locations_{instance.search_history.user.id}"
        cache.delete(cache_key)


@receiver(post_delete, sender=SearchHistory)
def handle_search_deleted(sender, instance, **kwargs):
    """Handle search deletion."""
    logger.info(f"Search deleted: {instance.id} by {instance.user.email}")