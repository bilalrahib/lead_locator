from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.accounts.models import UserActivity
from .models import ClientProfile, ClientSavedSearch, ClientLocationData, WhiteLabelSettings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=ClientProfile)
def client_profile_post_save(sender, instance, created, **kwargs):
    """Handle client profile creation/updates."""
    if created:
        logger.info(f"New client profile created: {instance.client_name} for user {instance.user.email}")
        
        # Create default white label settings for Professional users
        if instance.user.subscription_status == 'PROFESSIONAL':
            try:
                WhiteLabelSettings.objects.get_or_create(
                    user=instance.user,
                    defaults={
                        'company_name': f"{instance.user.first_name} {instance.user.last_name}".strip() or "Your Company",
                        'company_email': instance.user.email,
                        'is_active': True
                    }
                )
            except Exception as e:
                logger.error(f"Error creating white label settings for {instance.user.email}: {e}")


@receiver(post_save, sender=ClientSavedSearch)
def client_search_post_save(sender, instance, created, **kwargs):
    """Handle client search creation."""
    if created:
        logger.info(f"New client search created: {instance.search_name} for {instance.client_profile.client_name}")
        
        # Update user activity
        try:
            UserActivity.log_activity(
                user=instance.client_profile.user,
                activity_type='client_search_created',
                description=f'Created search "{instance.search_name}" for client {instance.client_profile.client_name}',
                metadata={
                    'client_id': str(instance.client_profile.id),
                    'search_id': str(instance.id),
                    'search_name': instance.search_name
                }
            )
        except Exception as e:
            logger.error(f"Error logging client search activity: {e}")


@receiver(post_save, sender=ClientLocationData)
def client_location_post_save(sender, instance, created, **kwargs):
    """Handle client location assignments."""
    if created:
        logger.info(f"Location {instance.location_data.name} assigned to client {instance.client_profile.client_name}")
    else:
        # Log status changes
        if 'status' in kwargs.get('update_fields', []):
            logger.info(f"Location {instance.location_data.name} status changed to {instance.status} for client {instance.client_profile.client_name}")


@receiver(post_delete, sender=ClientProfile)
def client_profile_post_delete(sender, instance, **kwargs):
    """Handle client profile deletion."""
    logger.info(f"Client profile deleted: {instance.client_name} for user {instance.user.email}")


@receiver(post_save, sender=User)
def user_subscription_changed(sender, instance, **kwargs):
    """Handle user subscription changes that affect pro features."""
    if hasattr(instance, '_subscription_changed'):
        old_status = getattr(instance, '_old_subscription_status', None)
        new_status = instance.subscription_status
        
        # If user upgraded to Professional, create white label settings
        if old_status != 'PROFESSIONAL' and new_status == 'PROFESSIONAL':
            try:
                WhiteLabelSettings.objects.get_or_create(
                    user=instance,
                    defaults={
                        'company_name': f"{instance.first_name} {instance.last_name}".strip() or "Your Company",
                        'company_email': instance.email,
                        'is_active': True
                    }
                )
                logger.info(f"Created white label settings for upgraded user {instance.email}")
            except Exception as e:
                logger.error(f"Error creating white label settings for upgraded user {instance.email}: {e}")
        
        # If user downgraded from Professional, deactivate white label settings
        elif old_status == 'PROFESSIONAL' and new_status != 'PROFESSIONAL':
            try:
                white_label = WhiteLabelSettings.objects.filter(user=instance).first()
                if white_label:
                    white_label.is_active = False
                    white_label.save()
                    logger.info(f"Deactivated white label settings for downgraded user {instance.email}")
            except Exception as e:
                logger.error(f"Error deactivating white label settings for downgraded user {instance.email}: {e}")