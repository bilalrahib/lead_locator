from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ManagedLocation, PlacedMachine, VisitLog, CollectionData
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ManagedLocation)
def clear_location_cache(sender, instance, **kwargs):
    """Clear location-related cache when locations are modified."""
    cache_keys = [
        f'user_locations_{instance.user_id}',
        f'location_summary_{instance.user_id}'
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    logger.info(f"Location cache cleared for user {instance.user_id}")


@receiver(post_save, sender=PlacedMachine)
def handle_machine_placement(sender, instance, created, **kwargs):
    """Handle machine placement events."""
    if created:
        logger.info(f"New machine placed: {instance.get_machine_type_display()} at {instance.managed_location.location_name}")
    
    # Clear related caches
    cache.delete(f'user_machines_{instance.managed_location.user_id}')
    cache.delete(f'location_machines_{instance.managed_location_id}')


@receiver(post_save, sender=CollectionData)
def handle_collection_update(sender, instance, **kwargs):
    """Handle collection data updates."""
    logger.info(f"Collection recorded: ${instance.cash_collected} from {instance.visit_log.placed_machine}")
    
    # Clear financial summary caches
    user_id = instance.visit_log.placed_machine.managed_location.user_id
    cache.delete(f'financial_summary_{user_id}')
    cache.delete(f'machine_performance_{instance.visit_log.placed_machine_id}')


@receiver(post_delete, sender=ManagedLocation)
def handle_location_deletion(sender, instance, **kwargs):
    """Handle location deletion."""
    logger.info(f"Location deleted: {instance.location_name}")
    
    # Clear all related caches
    cache.delete(f'user_locations_{instance.user_id}')
    cache.delete(f'location_summary_{instance.user_id}')