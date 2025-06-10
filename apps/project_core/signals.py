from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.contrib.auth import get_user_model
from .models import SystemNotification, ContactMessage, SupportTicket
from .services import EmailService
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=SystemNotification)
@receiver(post_delete, sender=SystemNotification)
def clear_notification_cache(sender, **kwargs):
    """
    Clear notification cache when notifications are created, updated, or deleted.
    """
    cache_keys = [
        'active_notifications_None',
        'active_notifications_True',
        'active_notifications_False'
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    logger.info("Notification cache cleared")


@receiver(post_save, sender=ContactMessage)
def handle_contact_message_created(sender, instance, created, **kwargs):
    """
    Handle actions when a contact message is created.
    """
    if created:
        logger.info(f"New contact message received from {instance.email}")
        
        # Send notification email to admin (this is already handled in the view,
        # but we can add additional logic here if needed)
        pass


@receiver(post_save, sender=SupportTicket)
def handle_support_ticket_updated(sender, instance, created, **kwargs):
    """
    Handle actions when a support ticket is created or updated.
    """
    if created:
        logger.info(f"New support ticket created: {instance.id} by {instance.user.username}")
    else:
        logger.info(f"Support ticket updated: {instance.id} - Status: {instance.status}")
        
        # If ticket was just resolved, we could send a notification email
        if instance.status == 'resolved' and instance.resolved_at:
            # Additional logic for resolved tickets
            pass


@receiver(post_save, sender=User)
def handle_user_created(sender, instance, created, **kwargs):
    """
    Handle actions when a new user is created.
    """
    if created:
        logger.info(f"New user created: {instance.username}")
        
        # Send welcome email
        try:
            email_service = EmailService()
            email_service.send_welcome_email(instance)
        except Exception as e:
            logger.error(f"Failed to send welcome email to {instance.email}: {e}")