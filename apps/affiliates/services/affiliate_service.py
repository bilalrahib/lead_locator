from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, Avg
from typing import Dict, List, Optional
from datetime import timedelta, datetime
from decimal import Decimal
import logging

from ..models import AffiliateProfile, ReferralClick, ReferralConversion, AffiliateResource

User = get_user_model()
logger = logging.getLogger(__name__)


class AffiliateService:
    """Service for affiliate management operations."""

    @staticmethod
    @transaction.atomic
    def create_affiliate_application(user: User, application_data: Dict) -> AffiliateProfile:
        """
        Create new affiliate application.
        
        Args:
            user: User applying to become affiliate
            application_data: Application details
            
        Returns:
            AffiliateProfile: Created affiliate profile
        """
        # Check if user already has an affiliate profile
        if hasattr(user, 'affiliate_profile'):
            raise ValueError("User already has an affiliate application")
        
        affiliate = AffiliateProfile.objects.create(
            user=user,
            **application_data
        )
        
        logger.info(f"Affiliate application created for user {user.email}")
        return affiliate

    @staticmethod
    def get_affiliate_dashboard_data(affiliate: AffiliateProfile) -> Dict:
        """
        Get comprehensive dashboard data for affiliate.
        
        Args:
            affiliate: AffiliateProfile instance
            
        Returns:
            Dict with dashboard data
        """
        # Recent clicks (last 30 days)
        recent_clicks = ReferralClick.objects.filter(
            affiliate=affiliate,
            timestamp__gte=timezone.now() - timedelta(days=30)
        ).order_by('-timestamp')[:10]
        
        # Recent conversions
        recent_conversions = ReferralConversion.objects.filter(
            affiliate=affiliate
        ).order_by('-timestamp')[:10]
        
        # Earnings summary
        earnings_summary = AffiliateService.get_earnings_summary(affiliate)
        
        # Performance metrics
        performance_metrics = AffiliateService.get_performance_metrics(affiliate)
        
        # Available resources
        available_resources = AffiliateResource.objects.filter(
            is_active=True
        ).order_by('-created_at')
        
        return {
            'profile': affiliate,
            'recent_clicks': recent_clicks,
            'recent_conversions': recent_conversions,
            'earnings_summary': earnings_summary,
            'performance_metrics': performance_metrics,
            'available_resources': available_resources
        }

    @staticmethod
    def get_earnings_summary(affiliate: AffiliateProfile) -> Dict:
        """
        Get earnings summary for affiliate.
        
        Args:
            affiliate: AffiliateProfile instance
            
        Returns:
            Dict with earnings data
        """
        from ..models import CommissionLedger
        
        # Total earnings
        total_earnings = affiliate.get_total_earnings()
        pending_earnings = affiliate.get_pending_earnings()
        paid_earnings = CommissionLedger.objects.filter(
            affiliate=affiliate,
            status='paid'
        ).aggregate(total=Sum('amount_earned'))['total'] or Decimal('0.00')
        
        # This month earnings
        current_month = timezone.now().strftime('%Y-%m')
        this_month_earnings = CommissionLedger.objects.filter(
            affiliate=affiliate,
            month_year=current_month
        ).aggregate(total=Sum('amount_earned'))['total'] or Decimal('0.00')
        
        # Last month earnings
        last_month = (timezone.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
        last_month_earnings = CommissionLedger.objects.filter(
            affiliate=affiliate,
            month_year=last_month
        ).aggregate(total=Sum('amount_earned'))['total'] or Decimal('0.00')
        
        # Conversion metrics
        total_conversions = affiliate.conversions.count()
        active_referrals = affiliate.conversions.filter(
            referred_user__subscription__is_active=True
        ).count()
        
        # Calculate conversion rate
        total_clicks = affiliate.referral_clicks.count()
        conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        
        return {
            'total_earnings': total_earnings,
            'pending_earnings': pending_earnings,
            'paid_earnings': paid_earnings,
            'this_month_earnings': this_month_earnings,
            'last_month_earnings': last_month_earnings,
            'total_conversions': total_conversions,
            'active_referrals': active_referrals,
            'conversion_rate': round(conversion_rate, 2)
        }

    @staticmethod
    def get_performance_metrics(affiliate: AffiliateProfile, days: int = 30) -> Dict:
        """
        Get performance metrics for affiliate.
        
        Args:
            affiliate: AffiliateProfile instance
            days: Number of days to analyze
            
        Returns:
            Dict with performance metrics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Clicks in period
        clicks_in_period = affiliate.referral_clicks.filter(
            timestamp__gte=start_date
        ).count()
        
        # Conversions in period
        conversions_in_period = affiliate.conversions.filter(
            timestamp__gte=start_date
        ).count()
        
        # Top traffic sources
        top_sources = affiliate.referral_clicks.filter(
            timestamp__gte=start_date,
            referrer_url__isnull=False
        ).exclude(
            referrer_url=''
        ).values('referrer_url').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Daily performance (last 7 days)
        daily_performance = []
        for i in range(7):
            day = (end_date - timedelta(days=i)).date()
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            
            clicks = affiliate.referral_clicks.filter(
                timestamp__range=[day_start, day_end]
            ).count()
            
            conversions = affiliate.conversions.filter(
                timestamp__range=[day_start, day_end]
            ).count()
            
            daily_performance.append({
                'date': day.isoformat(),
                'clicks': clicks,
                'conversions': conversions
            })
        
        return {
            'clicks_in_period': clicks_in_period,
            'conversions_in_period': conversions_in_period,
            'conversion_rate_period': (conversions_in_period / clicks_in_period * 100) if clicks_in_period > 0 else 0,
            'top_traffic_sources': list(top_sources),
            'daily_performance': daily_performance
        }

    @staticmethod
    @transaction.atomic
    def approve_affiliate(affiliate_id: str, admin_user: User) -> bool:
        """
        Approve affiliate application.
        
        Args:
            affiliate_id: Affiliate profile ID
            admin_user: Admin user approving
            
        Returns:
            bool: True if successful
        """
        try:
            affiliate = AffiliateProfile.objects.get(id=affiliate_id)
            
            # Manual approval to avoid tracker issues
            affiliate.status = 'approved'
            affiliate.approved_at = timezone.now()
            affiliate.approved_by = admin_user
            affiliate.save()
            
            # Update user's affiliate status - NO update_fields
            affiliate.user.is_approved_affiliate = True
            affiliate.user.save()
            
            logger.info(f"Affiliate {affiliate.referral_code} approved by {admin_user.email}")
            return True
            
        except AffiliateProfile.DoesNotExist:
            logger.error(f"Affiliate profile {affiliate_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error approving affiliate: {e}")
            return False
    # @staticmethod
    # @transaction.atomic
    # def approve_affiliate(affiliate_id: str, admin_user: User) -> bool:
    #     """
    #     Approve affiliate application.
        
    #     Args:
    #         affiliate_id: Affiliate profile ID
    #         admin_user: Admin user approving
            
    #     Returns:
    #         bool: True if successful
    #     """
    #     try:
    #         affiliate = AffiliateProfile.objects.get(id=affiliate_id)
    #         affiliate.approve(admin_user)
            
    #         logger.info(f"Affiliate {affiliate.referral_code} approved by {admin_user.email}")
    #         return True
            
    #     except AffiliateProfile.DoesNotExist:
    #         logger.error(f"Affiliate profile {affiliate_id} not found")
    #         return False
    #     except Exception as e:
    #         logger.error(f"Error approving affiliate: {e}")
    #         return False
    
    
    # def approve_affiliate(affiliate_id: str, admin_user: User) -> bool:
    #     """
    #     Approve affiliate application.
        
    #     Args:
    #         affiliate_id: Affiliate profile ID
    #         admin_user: Admin user approving
            
    #     Returns:
    #         bool: True if successful
    #     """
    #     try:
    #         affiliate = AffiliateProfile.objects.get(id=affiliate_id)
    #         affiliate.approve(admin_user)
            
    #         # Send approval email (implement in email service)
    #         from apps.project_core.services import EmailService
    #         email_service = EmailService()
    #         # email_service.send_affiliate_approval_email(affiliate)
            
    #         logger.info(f"Affiliate {affiliate.referral_code} approved by {admin_user.email}")
    #         return True
            
    #     except AffiliateProfile.DoesNotExist:
    #         logger.error(f"Affiliate profile {affiliate_id} not found")
    #         return False
    #     except Exception as e:
    #         logger.error(f"Error approving affiliate: {e}")
    #         return False

    @staticmethod
    @transaction.atomic
    def update_payout_info(affiliate: AffiliateProfile, payout_data: Dict) -> bool:
        """
        Update affiliate payout information.
        
        Args:
            affiliate: AffiliateProfile instance
            payout_data: Payout information
            
        Returns:
            bool: True if successful
        """
        try:
            for field, value in payout_data.items():
                if hasattr(affiliate, field):
                    setattr(affiliate, field, value)
            
            affiliate.save()
            logger.info(f"Payout info updated for affiliate {affiliate.referral_code}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating payout info: {e}")
            return False

    @staticmethod
    def get_affiliate_leaderboard(limit: int = 10) -> List[Dict]:
        """
        Get affiliate leaderboard by earnings.
        
        Args:
            limit: Number of top affiliates to return
            
        Returns:
            List of affiliate data with rankings
        """
        from ..models import CommissionLedger
        
        # Get top affiliates by total earnings
        top_affiliates = AffiliateProfile.objects.filter(
            status='approved'
        ).annotate(
            total_earnings=Sum('commission_ledger__amount_earned'),
            total_conversions=Count('conversions')
        ).filter(
            total_earnings__gt=0
        ).order_by('-total_earnings')[:limit]
        
        leaderboard = []
        for rank, affiliate in enumerate(top_affiliates, 1):
            leaderboard.append({
                'rank': rank,
                'affiliate_code': affiliate.referral_code,
                'user_name': affiliate.user.full_name,
                'total_earnings': float(affiliate.total_earnings or 0),
                'total_conversions': affiliate.total_conversions,
                'join_date': affiliate.approved_at
            })
        
        return leaderboard

    @staticmethod
    def track_resource_download(resource_id: str, affiliate: AffiliateProfile):
        """
        Track when an affiliate downloads a resource.
        
        Args:
            resource_id: Resource ID
            affiliate: AffiliateProfile instance
        """
        try:
            resource = AffiliateResource.objects.get(id=resource_id)
            resource.increment_download_count()
            
            logger.info(f"Resource {resource.title} downloaded by {affiliate.referral_code}")
            
        except AffiliateResource.DoesNotExist:
            logger.error(f"Resource {resource_id} not found")