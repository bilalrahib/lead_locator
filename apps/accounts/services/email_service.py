from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.urls import reverse
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class UserEmailService:
    """
    Service for sending user-related emails.
    """

    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.company_name = settings.VENDING_HIVE.get('COMPANY_NAME', 'Vending Hive')
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

    def send_welcome_email(self, user) -> bool:
        """
        Send welcome email to new user.
        
        Args:
            user: User instance
            
        Returns:
            True if email sent successfully
        """
        try:
            if not user.can_receive_email('notification'):
                return False

            subject = f"Welcome to {self.company_name}!"
            
            context = {
                'user': user,
                'company_name': self.company_name,
                'login_url': f"{self.frontend_url}/login",
                'dashboard_url': f"{self.frontend_url}/dashboard",
                'support_url': f"{self.frontend_url}/support",
            }
            
            html_content = render_to_string('accounts/emails/welcome_email.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending welcome email to {user.email}: {e}")
            return False

    def send_verification_email(self, user, token: str = None) -> bool:
        """
        Send email verification email.
        
        Args:
            user: User instance
            token: Verification token (if not provided, will use user's token)
            
        Returns:
            True if email sent successfully
        """
        try:
            verification_token = token or user.email_verification_token
            if not verification_token:
                logger.error(f"No verification token for user {user.email}")
                return False

            subject = f"Verify your {self.company_name} email address"
            verification_url = f"{self.frontend_url}/verify-email/{verification_token}"
            
            context = {
                'user': user,
                'company_name': self.company_name,
                'verification_url': verification_url,
                'verification_token': verification_token,
            }
            
            html_content = render_to_string('accounts/emails/email_verification.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending verification email to {user.email}: {e}")
            return False

    def send_password_reset_email(self, user, token: str) -> bool:
        """
        Send password reset email.
        
        Args:
            user: User instance
            token: Password reset token
            
        Returns:
            True if email sent successfully
        """
        try:
            subject = f"Reset your {self.company_name} password"
            reset_url = f"{self.frontend_url}/reset-password/{token}"
            
            context = {
                'user': user,
                'company_name': self.company_name,
                'reset_url': reset_url,
                'token': token,
            }
            
            html_content = render_to_string('accounts/emails/password_reset.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending password reset email to {user.email}: {e}")
            return False

    def send_password_changed_notification(self, user) -> bool:
        """
        Send notification when password is changed.
        
        Args:
            user: User instance
            
        Returns:
            True if email sent successfully
        """
        try:
            if not user.can_receive_email('notification'):
                return False

            subject = f"Your {self.company_name} password was changed"
            
            context = {
                'user': user,
                'company_name': self.company_name,
                'support_url': f"{self.frontend_url}/support",
                'login_url': f"{self.frontend_url}/login",
            }
            
            html_content = render_to_string('accounts/emails/password_changed.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending password changed notification to {user.email}: {e}")
            return False

    def send_email_changed_notification(self, user, old_email: str) -> bool:
        """
        Send notification when email is changed.
        
        Args:
            user: User instance
            old_email: Previous email address
            
        Returns:
            True if email sent successfully
        """
        try:
            subject = f"Your {self.company_name} email address was changed"
            
            context = {
                'user': user,
                'company_name': self.company_name,
                'old_email': old_email,
                'new_email': user.email,
                'support_url': f"{self.frontend_url}/support",
            }
            
            html_content = render_to_string('accounts/emails/email_changed.html', context)
            text_content = strip_tags(html_content)
            
            # Send to both old and new email addresses
            recipients = [old_email, user.email]
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=recipients,
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending email changed notification: {e}")
            return False

    def send_account_locked_notification(self, user) -> bool:
        """
        Send notification when account is locked.
        
        Args:
            user: User instance
            
        Returns:
            True if email sent successfully
        """
        try:
            subject = f"Your {self.company_name} account has been locked"
            
            context = {
                'user': user,
                'company_name': self.company_name,
                'support_url': f"{self.frontend_url}/support",
                'unlock_time': user.lock_expires_at,
            }
            
            html_content = render_to_string('accounts/emails/account_locked.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending account locked notification to {user.email}: {e}")
            return False

    def send_subscription_welcome_email(self, user, subscription) -> bool:
        """
        Send welcome email for new subscription.
        
        Args:
            user: User instance
            subscription: Subscription instance
            
        Returns:
            True if email sent successfully
        """
        try:
            if not user.can_receive_email('notification'):
                return False

            subject = f"Welcome to {subscription.plan.get_name_display()}!"
            
            context = {
                'user': user,
                'subscription': subscription,
                'plan': subscription.plan,
                'company_name': self.company_name,
                'dashboard_url': f"{self.frontend_url}/dashboard",
                'features_url': f"{self.frontend_url}/features",
            }
            
            html_content = render_to_string('accounts/emails/subscription_welcome.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending subscription welcome email to {user.email}: {e}")
            return False

    def send_marketing_email(self, user, subject: str, template_name: str, context: dict = None) -> bool:
        """
        Send marketing email.
        
        Args:
            user: User instance
            subject: Email subject
            template_name: Template name
            context: Template context
            
        Returns:
            True if email sent successfully
        """
        try:
            if not user.can_receive_email('marketing'):
                return False

            email_context = {
                'user': user,
                'company_name': self.company_name,
                'unsubscribe_url': f"{self.frontend_url}/unsubscribe/{user.id}",
                **(context or {})
            }
            
            html_content = render_to_string(f'accounts/emails/marketing/{template_name}', email_context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending marketing email to {user.email}: {e}")
            return False

    def _send_email(self, subject: str, message: str, recipient_list: list, 
                   html_message: Optional[str] = None) -> bool:
        """
        Internal method to send email.
        
        Args:
            subject: Email subject
            message: Text message
            recipient_list: List of recipients
            html_message: Optional HTML message
            
        Returns:
            True if successful
        """
        try:
            if html_message:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=message,
                    from_email=self.from_email,
                    to=recipient_list
                )
                email.attach_alternative(html_message, "text/html")
                email.send()
            else:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=self.from_email,
                    recipient_list=recipient_list,
                    fail_silently=False
                )
            
            logger.info(f"Email sent successfully to {len(recipient_list)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False