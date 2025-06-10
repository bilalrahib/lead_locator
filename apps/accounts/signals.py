from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.utils import timezone
from .models import CustomUser, UserProfile, UserActivity
from .services import UserEmailService
import logging


from apps.affiliates.services import ReferralService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create user profile when user is created.
    """
    if created:
        UserProfile.objects.create(user=instance)
        logger.info(f"Profile created for user: {instance.email}")


@receiver(post_save, sender=CustomUser)
def handle_user_email_verification(sender, instance, **kwargs):
    """
    Handle email verification status changes.
    """
    if instance.email_verified and 'email_verified' in getattr(instance, '_state', {}).get('fields_cache', {}):
        # Email was just verified
        UserActivity.log_activity(
            user=instance,
            activity_type='email_verification',
            description='Email address verified'
        )
        logger.info(f"Email verified for user: {instance.email}")


@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """
    Handle successful user login.
    """
    from apps.project_core.utils.helpers import get_client_ip
    
    # Update last activity and IP
    ip_address = get_client_ip(request) if request else None
    user.update_last_activity(ip_address)
    
    # Reset failed attempts
    user.reset_failed_attempts()
    
    # Log login activity
    UserActivity.log_activity(
        user=user,
        activity_type='login',
        description='User logged in successfully',
        request=request
    )
    
    logger.info(f"User logged in: {user.email}")


@receiver(user_logged_out)
def handle_user_logout(sender, request, user, **kwargs):
    """
    Handle user logout.
    """
    if user:
        # Log logout activity
        UserActivity.log_activity(
            user=user,
            activity_type='logout',
            description='User logged out',
            request=request
        )
        
        logger.info(f"User logged out: {user.email}")


@receiver(user_login_failed)
def handle_failed_login(sender, credentials, request, **kwargs):
    """
    Handle failed login attempts.
    """
    email = credentials.get('email') or credentials.get('username')
    
    if email:
        try:
            user = CustomUser.objects.get(email__iexact=email)
            user.increment_failed_attempts()
            
            # Log failed login
            UserActivity.log_activity(
                user=user,
                activity_type='login_failed',
                description='Failed login attempt',
                request=request
            )
            
            # Send email if account gets locked
            if user.is_account_locked:
                email_service = UserEmailService()
                email_service.send_account_locked_notification(user)
            
            logger.warning(f"Failed login attempt for: {email}")
            
        except CustomUser.DoesNotExist:
            logger.warning(f"Failed login attempt for non-existent email: {email}")


@receiver(pre_save, sender=CustomUser)
def handle_user_changes(sender, instance, **kwargs):
    """
    Handle changes to user model.
    """
    if instance.pk:  # User already exists
        try:
            old_instance = CustomUser.objects.get(pk=instance.pk)
            
            # Check for email change
            if old_instance.email != instance.email:
                # Email changed - require re-verification
                instance.email_verified = False
                instance.generate_email_verification_token()
                
                logger.info(f"Email changed for user {old_instance.email} to {instance.email}")
            
            # Check for password change
            if old_instance.password != instance.password:
                # Password changed
                UserActivity.log_activity(
                    user=instance,
                    activity_type='password_change',
                    description='Password changed'
                )
                
                logger.info(f"Password changed for user: {instance.email}")
                
        except CustomUser.DoesNotExist:
            pass


@receiver(post_save, sender=UserProfile)
def handle_profile_completion(sender, instance, **kwargs):
    """
    Handle profile completion status.
    """
    completion = instance.completion_percentage
    
    if completion >= 80 and not instance.profile_completed:
        instance.mark_completed()
        
        # Log profile completion
        UserActivity.log_activity(
            user=instance.user,
            activity_type='profile_completed',
            description='Profile marked as completed',
            metadata={'completion_percentage': completion}
        )
        
        logger.info(f"Profile completed for user: {instance.user.email}")


@receiver(post_delete, sender=CustomUser)
def handle_user_deletion(sender, instance, **kwargs):
    """
    Handle user account deletion.
    """
    logger.info(f"User account deleted: {instance.email}")


# Custom signal for subscription changes
def handle_subscription_change(sender, user, old_plan, new_plan, **kwargs):
    """
    Handle subscription plan changes.
    This will be connected by the subscriptions app.
    """
    UserActivity.log_activity(
        user=user,
        activity_type='subscription_change',
        description=f'Subscription changed from {old_plan} to {new_plan}',
        metadata={
            'old_plan': old_plan,
            'new_plan': new_plan
        }
    )
    
    logger.info(f"Subscription changed for {user.email}: {old_plan} -> {new_plan}")


# Add this signal handler
@receiver(post_save, sender=User)
def handle_new_user_referral(sender, instance, created, **kwargs):
    """Handle referral conversion when new user is created."""
    if created:
        # Process referral conversion if this is a referred user
        # Note: request object needs to be passed somehow - this is a simplified version
        # In practice, you'd need to handle this in the registration view
        pass