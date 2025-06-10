from django.contrib.auth import get_user_model
from typing import Dict, Optional
import logging

from ..models import WhiteLabelSettings

User = get_user_model()
logger = logging.getLogger(__name__)


class WhiteLabelService:
    """Service for managing white label settings."""

    @staticmethod
    def get_or_create_settings(user: User) -> WhiteLabelSettings:
        """
        Get or create white label settings for a user.
        
        Args:
            user: User instance
            
        Returns:
            WhiteLabelSettings instance
        """
        if user.subscription_status != 'PROFESSIONAL':
            raise ValueError("White-label features are only available for Professional plan users")

        settings, created = WhiteLabelSettings.objects.get_or_create(
            user=user,
            defaults={
                'company_name': user.company_name or f"{user.first_name} {user.last_name}".strip(),
                'company_email': user.email,
                'is_active': True
            }
        )

        if created:
            logger.info(f"Created white label settings for user {user.email}")

        return settings

    @staticmethod
    def update_settings(user: User, settings_data: Dict) -> WhiteLabelSettings:
        """
        Update white label settings.
        
        Args:
            user: User instance
            settings_data: Settings data to update
            
        Returns:
            Updated WhiteLabelSettings instance
        """
        settings = WhiteLabelService.get_or_create_settings(user)
        
        for field, value in settings_data.items():
            if hasattr(settings, field):
                setattr(settings, field, value)
        
        settings.save()
        
        logger.info(f"Updated white label settings for user {user.email}")
        return settings

    @staticmethod
    def get_branding_context(user: User) -> Dict:
        """
        Get branding context for templates and exports.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with branding information
        """
        try:
            settings = WhiteLabelSettings.objects.get(user=user, is_active=True)
            
            return {
                'company_name': settings.company_name,
                'company_logo': settings.company_logo.url if settings.company_logo else None,
                'primary_color': settings.primary_color,
                'secondary_color': settings.secondary_color,
                'company_website': settings.company_website,
                'company_phone': settings.company_phone,
                'company_email': settings.company_email,
                'custom_domain': settings.custom_domain,
                'remove_vending_hive_branding': settings.remove_vending_hive_branding,
                'has_custom_branding': settings.has_custom_branding
            }
        except WhiteLabelSettings.DoesNotExist:
            # Return default Vending Hive branding
            return {
                'company_name': 'Vending Hive',
                'company_logo': None,
                'primary_color': '#fb6d00',
                'secondary_color': '#ffffff',
                'company_website': 'https://vendinghive.com',
                'company_phone': '+1-555-VENDING',
                'company_email': 'support@vendinghive.com',
                'custom_domain': None,
                'remove_vending_hive_branding': False,
                'has_custom_branding': False
            }

    @staticmethod
    def validate_custom_domain(domain: str) -> bool:
        """
        Validate custom domain format.
        
        Args:
            domain: Domain to validate
            
        Returns:
            Boolean indicating if domain is valid
        """
        import re
        
        # Basic domain validation
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        
        if not re.match(domain_pattern, domain):
            return False
        
        # Check length
        if len(domain) > 255:
            return False
        
        # Additional checks can be added here
        return True

    @staticmethod
    def get_client_portal_url(user: User, client_id: str) -> str:
        """
        Get client portal URL with custom domain if configured.
        
        Args:
            user: User instance
            client_id: Client UUID
            
        Returns:
            Client portal URL
        """
        try:
            settings = WhiteLabelSettings.objects.get(user=user, is_active=True)
            if settings.custom_domain:
                return f"https://{settings.custom_domain}/client/{client_id}"
        except WhiteLabelSettings.DoesNotExist:
            pass
        
        # Default URL
        return f"https://app.vendinghive.com/pro/client/{client_id}"