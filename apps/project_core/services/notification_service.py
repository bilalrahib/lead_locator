from django.utils import timezone
from django.core.cache import cache
from django.db import models  # Add this import
from typing import List, Dict, Optional
from ..models import SystemNotification
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing system notifications.
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes

    def get_active_notifications(self, show_on_homepage: Optional[bool] = None) -> List[SystemNotification]:
        """
        Get all currently active notifications.
        
        Args:
            show_on_homepage: Filter by homepage visibility
            
        Returns:
            List of active SystemNotification objects
        """
        cache_key = f"active_notifications_{show_on_homepage}"
        notifications = cache.get(cache_key)
        
        if notifications is None:
            queryset = SystemNotification.objects.filter(
                is_active=True,
                start_date__lte=timezone.now()
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now())
            )
            
            if show_on_homepage is not None:
                queryset = queryset.filter(show_on_homepage=show_on_homepage)
            
            notifications = list(queryset.order_by('-created_at'))
            cache.set(cache_key, notifications, self.cache_timeout)
        
        return notifications

    def create_notification(self, title: str, message: str, notification_type: str = 'info',
                          show_on_homepage: bool = False, start_date: Optional[timezone.datetime] = None,
                          end_date: Optional[timezone.datetime] = None) -> SystemNotification:
        """
        Create a new system notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, warning, error, success, maintenance)
            show_on_homepage: Whether to show on homepage
            start_date: When to start showing notification
            end_date: When to stop showing notification
            
        Returns:
            Created SystemNotification object
        """
        try:
            notification = SystemNotification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                show_on_homepage=show_on_homepage,
                start_date=start_date or timezone.now(),
                end_date=end_date
            )
            
            # Clear cache
            self._clear_notification_cache()
            
            logger.info(f"Created notification: {title}")
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise

    def update_notification(self, notification_id: int, **kwargs) -> Optional[SystemNotification]:
        """
        Update an existing notification.
        
        Args:
            notification_id: ID of notification to update
            **kwargs: Fields to update
            
        Returns:
            Updated SystemNotification object or None if not found
        """
        try:
            notification = SystemNotification.objects.get(id=notification_id)
            
            for field, value in kwargs.items():
                if hasattr(notification, field):
                    setattr(notification, field, value)
            
            notification.save()
            
            # Clear cache
            self._clear_notification_cache()
            
            logger.info(f"Updated notification {notification_id}")
            return notification
            
        except SystemNotification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error updating notification {notification_id}: {e}")
            raise

    def deactivate_notification(self, notification_id: int) -> bool:
        """
        Deactivate a notification.
        
        Args:
            notification_id: ID of notification to deactivate
            
        Returns:
            bool: True if successful
        """
        try:
            updated = SystemNotification.objects.filter(
                id=notification_id
            ).update(
                is_active=False,
                end_date=timezone.now()
            )
            
            if updated:
                # Clear cache
                self._clear_notification_cache()
                logger.info(f"Deactivated notification {notification_id}")
                return True
            else:
                logger.warning(f"Notification {notification_id} not found for deactivation")
                return False
                
        except Exception as e:
            logger.error(f"Error deactivating notification {notification_id}: {e}")
            return False

    def create_maintenance_notification(self, start_time: timezone.datetime, 
                                      end_time: timezone.datetime, message: str = None) -> SystemNotification:
        """
        Create a maintenance notification.
        
        Args:
            start_time: Maintenance start time
            end_time: Maintenance end time
            message: Custom message (optional)
            
        Returns:
            Created SystemNotification object
        """
        default_message = (
            f"Scheduled maintenance from {start_time.strftime('%m/%d/%Y %I:%M %p')} "
            f"to {end_time.strftime('%m/%d/%Y %I:%M %p')} UTC. "
            "Service may be temporarily unavailable."
        )
        
        return self.create_notification(
            title="Scheduled Maintenance",
            message=message or default_message,
            notification_type='maintenance',
            show_on_homepage=True,
            start_date=start_time,
            end_date=end_time
        )

    def get_notification_stats(self) -> Dict:
        """
        Get statistics about notifications.
        
        Returns:
            Dict with notification statistics
        """
        try:
            total = SystemNotification.objects.count()
            active = SystemNotification.objects.filter(is_active=True).count()
            by_type = {}
            
            for notification_type, _ in SystemNotification.NOTIFICATION_TYPES:
                count = SystemNotification.objects.filter(
                    notification_type=notification_type,
                    is_active=True
                ).count()
                by_type[notification_type] = count
            
            return {
                'total': total,
                'active': active,
                'by_type': by_type,
                'current_active': len(self.get_active_notifications())
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {}

    def _clear_notification_cache(self):
        """Clear all notification-related cache entries."""
        cache_keys = [
            'active_notifications_None',
            'active_notifications_True',
            'active_notifications_False'
        ]
        
        for key in cache_keys:
            cache.delete(key)