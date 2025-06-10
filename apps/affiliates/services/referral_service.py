# from django.db import transaction
# from django.contrib.auth import get_user_model
# from django.utils import timezone
# from typing import Optional
# from django.db.models import Q, Count, Sum, Avg  # Add Count here

# from django.db import models
# import logging

# from ..models import AffiliateProfile, ReferralConversion, ReferralClick

# User = get_user_model()
# logger = logging.getLogger(__name__)


# class ReferralService:
#     """Service for handling referral tracking and conversions."""

#     @staticmethod
#     @transaction.atomic
#     def process_referral_conversion(user: User, request=None) -> Optional[ReferralConversion]:
#         """
#         Process referral conversion when user registers.
        
#         Args:
#             user: Newly registered user
#             request: HTTP request object
            
#         Returns:
#             ReferralConversion instance if created, None otherwise
#         """
#         if not request or not hasattr(request, 'session'):
#             return None
        
#         # Check for referral code in session
#         referral_code = request.session.get('referral_code')
#         affiliate_id = request.session.get('referral_affiliate_id')
        
#         if not referral_code or not affiliate_id:
#             return None
        
#         try:
#             # Get affiliate
#             affiliate = AffiliateProfile.objects.get(
#                 id=affiliate_id,
#                 referral_code=referral_code,
#                 status='approved'
#             )
            
#             # Check if user already has a referral source
#             if hasattr(user, 'referral_source'):
#                 logger.warning(f"User {user.email} already has referral source")
#                 return None
            
#             # Find the most recent click from this affiliate for this session
#             recent_click = ReferralClick.objects.filter(
#                 affiliate=affiliate,
#                 session_key=request.session.session_key
#             ).order_by('-timestamp').first()
            
#             # Create conversion
#             conversion = ReferralConversion.objects.create(
#                 affiliate=affiliate,
#                 referred_user=user,
#                 referral_click=recent_click,
#                 conversion_value=0  # Will be updated when user subscribes
#             )
            
#             # Clear referral from session
#             request.session.pop('referral_code', None)
#             request.session.pop('referral_affiliate_id', None)
            
#             logger.info(
#                 f"Referral conversion created: {user.email}  -> {affiliate.referral_code}"
#             )
            
#             return conversion
            
#         except AffiliateProfile.DoesNotExist:
#             logger.warning(f"Affiliate not found for referral: {referral_code}")
#             return None
#         except Exception as e:
#             logger.error(f"Error processing referral conversion: {e}")
#             return None

#     @staticmethod
#     def update_conversion_value(user: User, value: float):
#         """
#         Update conversion value when user takes valuable action (e.g., subscribes).
        
#         Args:
#             user: User who performed the action
#             value: Value of the action
#         """
#         try:
#             if hasattr(user, 'referral_source'):
#                 conversion = user.referral_source
#                 conversion.conversion_value += value
#                 conversion.save(update_fields=['conversion_value'])
                
#                 logger.info(
#                     f"Updated conversion value for {user.email}: +${value}"
#                 )
                
#         except Exception as e:
#             logger.error(f"Error updating conversion value: {e}")

#     @staticmethod
#     def get_referral_analytics(affiliate: AffiliateProfile, days: int = 30) -> dict:
#         """
#         Get referral analytics for affiliate.
        
#         Args:
#             affiliate: AffiliateProfile instance
#             days: Number of days to analyze
            
#         Returns:
#             Dict with analytics data
#         """
#         end_date = timezone.now()
#         start_date = end_date - timezone.timedelta(days=days)
        
#         # Click analytics
#         total_clicks = affiliate.referral_clicks.count()
#         period_clicks = affiliate.referral_clicks.filter(
#             timestamp__gte=start_date
#         ).count()
        
#         # Conversion analytics
#         total_conversions = affiliate.conversions.count()
#         period_conversions = affiliate.conversions.filter(
#             timestamp__gte=start_date
#         ).count()
        
#         # Calculate rates
#         overall_conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
#         period_conversion_rate = (period_conversions / period_clicks * 100) if period_clicks > 0 else 0
        
#         # Top referring sources
#         top_sources = affiliate.referral_clicks.filter(
#             timestamp__gte=start_date,
#             referrer_url__isnull=False
#         ).exclude(
#             referrer_url=''
#         ).values('referrer_url').annotate(
#             count=Count('id')
#         ).order_by('-count')[:5]
        
#         # Geographic data (by IP - simplified)
#         # In production, you'd use a GeoIP service
#         click_countries = affiliate.referral_clicks.filter(
#             timestamp__gte=start_date
#         ).values('ip_address').distinct().count()
        
#         return {
#             'total_clicks': total_clicks,
#             'period_clicks': period_clicks,
#             'total_conversions': total_conversions,
#             'period_conversions': period_conversions,
#             'overall_conversion_rate': round(overall_conversion_rate, 2),
#             'period_conversion_rate': round(period_conversion_rate, 2),
#             'top_sources': list(top_sources),
#             'unique_visitors': click_countries,
#             'period_days': days
#         }

#     @staticmethod
#     def generate_referral_link(affiliate: AffiliateProfile, campaign: str = None, 
#                              source: str = None) -> str:
#         """
#         Generate tracking referral link for affiliate.
        
#         Args:
#             affiliate: AffiliateProfile instance
#             campaign: Optional campaign identifier
#             source: Optional source identifier
            
#         Returns:
#             Generated referral URL
#         """
#         from django.conf import settings
        
#         base_url = getattr(settings, 'FRONTEND_URL', 'https://vendinghive.com')
#         url = f"{base_url}/?ref={affiliate.referral_code}"
        
#         # Add optional tracking parameters
#         params = []
#         if campaign:
#             params.append(f"utm_campaign={campaign}")
#         if source:
#             params.append(f"utm_source={source}")
        
#         if params:
#             url += "&" + "&".join(params)
        
#         return url
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q
from typing import Optional
import logging

from ..models import AffiliateProfile, ReferralConversion, ReferralClick

User = get_user_model()
logger = logging.getLogger(__name__)


class ReferralService:
    """Service for handling referral tracking and conversions."""

    @staticmethod
    @transaction.atomic
    def process_referral_conversion(user: User, request=None) -> Optional[ReferralConversion]:
        """
        Process referral conversion when user registers.
        
        Args:
            user: Newly registered user
            request: HTTP request object
            
        Returns:
            ReferralConversion instance if created, None otherwise
        """
        if not request or not hasattr(request, 'session'):
            return None
        
        # Check for referral code in session
        referral_code = request.session.get('referral_code')
        affiliate_id = request.session.get('referral_affiliate_id')
        
        if not referral_code or not affiliate_id:
            return None
        
        try:
            # Get affiliate
            affiliate = AffiliateProfile.objects.get(
                id=affiliate_id,
                referral_code=referral_code,
                status='approved'
            )
            
            # Check if user already has a referral source
            if hasattr(user, 'referral_source'):
                logger.warning(f"User {user.email} already has referral source")
                return None
            
            # Find the most recent click from this affiliate for this session
            recent_click = ReferralClick.objects.filter(
                affiliate=affiliate,
                session_key=request.session.session_key
            ).order_by('-timestamp').first()
            
            # Create conversion
            conversion = ReferralConversion.objects.create(
                affiliate=affiliate,
                referred_user=user,
                referral_click=recent_click,
                conversion_value=0  # Will be updated when user subscribes
            )
            
            # Clear referral from session
            request.session.pop('referral_code', None)
            request.session.pop('referral_affiliate_id', None)
            
            logger.info(
                f"Referral conversion created: {user.email} -> {affiliate.referral_code}"
            )
            
            return conversion
            
        except AffiliateProfile.DoesNotExist:
            logger.warning(f"Affiliate not found for referral: {referral_code}")
            return None
        except Exception as e:
            logger.error(f"Error processing referral conversion: {e}")
            return None

    @staticmethod
    def update_conversion_value(user: User, value: float):
        """
        Update conversion value when user takes valuable action (e.g., subscribes).
        
        Args:
            user: User who performed the action
            value: Value of the action
        """
        try:
            if hasattr(user, 'referral_source'):
                conversion = user.referral_source
                conversion.conversion_value += value
                conversion.save(update_fields=['conversion_value'])
                
                logger.info(
                    f"Updated conversion value for {user.email}: +${value}"
                )
                
        except Exception as e:
            logger.error(f"Error updating conversion value: {e}")

    @staticmethod
    def get_referral_analytics(affiliate: AffiliateProfile, days: int = 30) -> dict:
        """
        Get referral analytics for affiliate.
        
        Args:
            affiliate: AffiliateProfile instance
            days: Number of days to analyze
            
        Returns:
            Dict with analytics data
        """
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)
        
        # Click analytics
        total_clicks = affiliate.referral_clicks.count()
        period_clicks = affiliate.referral_clicks.filter(
            timestamp__gte=start_date
        ).count()
        
        # Conversion analytics
        total_conversions = affiliate.conversions.count()
        period_conversions = affiliate.conversions.filter(
            timestamp__gte=start_date
        ).count()
        
        # Calculate rates
        overall_conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        period_conversion_rate = (period_conversions / period_clicks * 100) if period_clicks > 0 else 0
        
        # Top referring sources
        top_sources = affiliate.referral_clicks.filter(
            timestamp__gte=start_date,
            referrer_url__isnull=False
        ).exclude(
            referrer_url=''
        ).values('referrer_url').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Geographic data (by IP - simplified)
        # In production, you'd use a GeoIP service
        click_countries = affiliate.referral_clicks.filter(
            timestamp__gte=start_date
        ).values('ip_address').distinct().count()
        
        return {
            'total_clicks': total_clicks,
            'period_clicks': period_clicks,
            'total_conversions': total_conversions,
            'period_conversions': period_conversions,
            'overall_conversion_rate': round(overall_conversion_rate, 2),
            'period_conversion_rate': round(period_conversion_rate, 2),
            'top_sources': list(top_sources),
            'unique_visitors': click_countries,
            'period_days': days
        }

    @staticmethod
    def generate_referral_link(affiliate: AffiliateProfile, campaign: str = None, 
                             source: str = None) -> str:
        """
        Generate tracking referral link for affiliate.
        
        Args:
            affiliate: AffiliateProfile instance
            campaign: Optional campaign identifier
            source: Optional source identifier
            
        Returns:
            Generated referral URL
        """
        from django.conf import settings
        
        base_url = getattr(settings, 'FRONTEND_URL', 'https://vendinghive.com')
        url = f"{base_url}/?ref={affiliate.referral_code}"
        
        # Add optional tracking parameters
        params = []
        if campaign:
            params.append(f"utm_campaign={campaign}")
        if source:
            params.append(f"utm_source={source}")
        
        if params:
            url += "&" + "&".join(params)
        
        return url