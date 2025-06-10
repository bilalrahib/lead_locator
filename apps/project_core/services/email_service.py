from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails with templates and notifications.
    """
    
    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.company_name = settings.VENDING_HIVE.get('COMPANY_NAME', 'Vending Hive')

    def send_support_ticket_confirmation(self, ticket) -> bool:
        """
        Send confirmation email when support ticket is created.
        
        Args:
            ticket: SupportTicket instance
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            subject = f"Support Ticket Created - #{ticket.id.hex[:8]}"
            
            context = {
                'ticket': ticket,
                'user': ticket.user,
                'company_name': self.company_name,
            }
            
            html_content = render_to_string('project_core/emails/support_ticket_created.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[ticket.user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending support ticket confirmation: {e}")
            return False

    def send_contact_form_notification(self, contact_message) -> bool:
        """
        Send notification email to admin when contact form is submitted.
        
        Args:
            contact_message: ContactMessage instance
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            subject = f"New Contact Form Submission: {contact_message.subject}"
            
            context = {
                'contact_message': contact_message,
                'company_name': self.company_name,
            }
            
            html_content = render_to_string('project_core/emails/contact_form_notification.html', context)
            text_content = strip_tags(html_content)
            
            admin_email = settings.VENDING_HIVE.get('COMPANY_EMAIL', 'admin@vendinghive.com')
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[admin_email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending contact form notification: {e}")
            return False

    def send_welcome_email(self, user) -> bool:
        """
        Send welcome email to new users.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            subject = f"Welcome to {self.company_name}!"
            
            context = {
                'user': user,
                'company_name': self.company_name,
                'login_url': settings.FRONTEND_URL + '/login' if hasattr(settings, 'FRONTEND_URL') else '#',
            }
            
            html_content = render_to_string('project_core/emails/welcome_email.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False

    def send_password_reset_email(self, user, reset_link: str) -> bool:
        """
        Send password reset email.
        
        Args:
            user: User instance
            reset_link: Password reset link
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            subject = f"Password Reset - {self.company_name}"
            
            context = {
                'user': user,
                'reset_link': reset_link,
                'company_name': self.company_name,
            }
            
            html_content = render_to_string('project_core/emails/password_reset.html', context)
            text_content = strip_tags(html_content)
            
            return self._send_email(
                subject=subject,
                message=text_content,
                recipient_list=[user.email],
                html_message=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return False

    def send_bulk_notification(self, subject: str, message: str, recipient_list: List[str], 
                             template_name: Optional[str] = None, context: Optional[Dict] = None) -> bool:
        """
        Send bulk notification emails.
        
        Args:
            subject: Email subject
            message: Email message (text)
            recipient_list: List of email addresses
            template_name: Optional HTML template name
            context: Optional template context
            
        Returns:
            bool: True if emails were sent successfully
        """
        try:
            html_message = None
            
            if template_name and context:
                html_message = render_to_string(template_name, context)
            
            return self._send_email(
                subject=subject,
                message=message,
                recipient_list=recipient_list,
                html_message=html_message
            )
            
        except Exception as e:
            logger.error(f"Error sending bulk notification: {e}")
            return False

    def _send_email(self, subject: str, message: str, recipient_list: List[str], 
                   html_message: Optional[str] = None) -> bool:
        """
        Internal method to send email.
        
        Args:
            subject: Email subject
            message: Text message
            recipient_list: List of recipients
            html_message: Optional HTML message
            
        Returns:
            bool: True if successful
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