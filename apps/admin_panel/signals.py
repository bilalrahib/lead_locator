from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import AdminLog, SystemSettings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=SystemSettings)
@receiver(post_delete, sender=SystemSettings)
def clear_settings_cache(sender, **kwargs):
    """Clear settings cache when system settings are modified."""
    cache_keys = [
        'system_settings_all',
        'system_settings_by_category'
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    logger.info("System settings cache cleared")


@receiver(post_save, sender=User)
def log_user_status_changes(sender, instance, created, **kwargs):
    """Log significant user status changes for audit purposes."""
    if not created and hasattr(instance, '_state'):
        # Check if important fields changed
        if instance.tracker.has_changed('is_active'):
            action_type = 'user_activate' if instance.is_active else 'user_deactivate'
            
            # Only log if this wasn't done through admin panel (to avoid duplicates)
            # We can check if there's a recent admin log for this action
            from django.utils import timezone
            from datetime import timedelta
            
            recent_log_exists = AdminLog.objects.filter(
                target_user=instance,
                action_type=action_type,
                created_at__gte=timezone.now() - timedelta(minutes=1)
            ).exists()
            
            if not recent_log_exists:
                AdminLog.objects.create(
                    admin_user=instance,  # Self-modification
                    action_type=action_type,
                    target_user=instance,
                    description=f"User account {'activated' if instance.is_active else 'deactivated'} (system)"
                )