from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, date
from typing import Dict, List
import logging

# from apps.project_core.models import SubscriptionPlan, UserSubscription, SupportTicket
try:
    from apps.project_core.models import SubscriptionPlan, UserSubscription, SupportTicket
except ImportError:
    SubscriptionPlan = None
    UserSubscription = None
    SupportTicket = None


# from apps.subscriptions.models import PaymentHistory, LeadCreditPackage
try:
    from apps.subscriptions.models import PaymentHistory, LeadCreditPackage
except ImportError:
    PaymentHistory = None
    LeadCreditPackage = None



from ..models import AdminDashboardStats

User = get_user_model()
logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics and reporting."""

    @staticmethod
    def get_dashboard_stats(force_refresh: bool = False) -> Dict:
        """
        Get dashboard statistics with caching.
        
        Args:
            force_refresh: Whether to force refresh cached data
            
        Returns:
            Dict with dashboard statistics
        """
        today = date.today()
        
        # Try to get cached stats
        if not force_refresh:
            try:
                cached_stats = AdminDashboardStats.objects.get(stat_date=today)
                # If cache is less than 1 hour old, use it
                if timezone.now() - cached_stats.updated_at < timedelta(hours=1):
                    return {
                        'total_users': cached_stats.total_users,
                        'new_users_today': cached_stats.new_users_today,
                        'active_subscriptions': cached_stats.active_subscriptions,
                        'revenue_today': cached_stats.revenue_today,
                        'searches_today': cached_stats.searches_today,
                        'support_tickets_open': cached_stats.support_tickets_open,
                        'additional_data': cached_stats.cache_data,
                        'last_updated': cached_stats.updated_at
                    }
            except AdminDashboardStats.DoesNotExist:
                pass
        
        # Calculate fresh stats
        stats = AnalyticsService._calculate_dashboard_stats()
        
        # Cache the results
        AdminDashboardStats.objects.update_or_create(
            stat_date=today,
            defaults={
                'total_users': stats['total_users'],
                'new_users_today': stats['new_users_today'],
                'active_subscriptions': stats['active_subscriptions'],
                'revenue_today': stats['revenue_today'],
                'searches_today': stats['searches_today'],
                'support_tickets_open': stats['support_tickets_open'],
                'cache_data': stats['additional_data']
            }
        )
        
        return stats

    @staticmethod
    def _calculate_dashboard_stats() -> Dict:
        """Calculate fresh dashboard statistics."""
        today = timezone.now().date()
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # User statistics
        total_users = User.objects.count()
        new_users_today = User.objects.filter(date_joined__gte=today_start).count()
        
        # Subscription statistics
        active_subscriptions = UserSubscription.objects.filter(is_active=True).count()
        
        # Revenue statistics
        revenue_today = PaymentHistory.objects.filter(
            created_at__gte=today_start,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Usage statistics (placeholder - will be updated when locator app is available)
        searches_today = 0
        
        # Support statistics
        support_tickets_open = SupportTicket.objects.filter(
            status__in=['open', 'in_progress']
        ).count()
        
        # Additional data for detailed analysis
        additional_data = {
            'user_growth_7_days': AnalyticsService._get_user_growth(7),
            'revenue_7_days': AnalyticsService._get_revenue_trend(7),
            'plan_distribution': AnalyticsService._get_plan_distribution(),
            'top_countries': AnalyticsService._get_top_countries(5)
        }
        
        return {
            'total_users': total_users,
            'new_users_today': new_users_today,
            'active_subscriptions': active_subscriptions,
            'revenue_today': float(revenue_today),
            'searches_today': searches_today,
            'support_tickets_open': support_tickets_open,
            'additional_data': additional_data,
            'last_updated': timezone.now()
        }

    @staticmethod
    def get_user_analytics(days: int = 30) -> Dict:
        """
        Get detailed user analytics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with user analytics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Basic counts
        total_users = User.objects.count()
        new_users_period = User.objects.filter(date_joined__gte=start_date).count()
        active_users_period = User.objects.filter(last_activity__gte=start_date).count()
        
        # Growth rate
        previous_period_start = start_date - timedelta(days=days)
        previous_new_users = User.objects.filter(
            date_joined__gte=previous_period_start,
            date_joined__lt=start_date
        ).count()
        
        growth_rate = 0
        if previous_new_users > 0:
            growth_rate = ((new_users_period - previous_new_users) / previous_new_users) * 100
        
        # Top countries
        top_countries = AnalyticsService._get_top_countries(10)
        
        # User distribution by plan
        user_by_plan = AnalyticsService._get_plan_distribution()
        
        # Email verification rate
        verified_users = User.objects.filter(email_verified=True).count()
        verification_rate = (verified_users / total_users * 100) if total_users > 0 else 0
        
        # Retention rate (users active in last 30 days)
        retention_users = User.objects.filter(
            last_activity__gte=timezone.now() - timedelta(days=30)
        ).count()
        retention_rate = (retention_users / total_users * 100) if total_users > 0 else 0
        
        return {
            'total_users': total_users,
            'new_users_this_period': new_users_period,
            'active_users_this_period': active_users_period,
            'user_growth_rate': growth_rate,
            'top_countries': top_countries,
            'user_by_plan': user_by_plan,
            'email_verification_rate': verification_rate,
            'user_retention_rate': retention_rate,
            'period_days': days
        }

    @staticmethod
    def get_revenue_analytics(days: int = 30) -> Dict:
        """
        Get detailed revenue analytics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with revenue analytics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Total revenue
        total_revenue = PaymentHistory.objects.filter(
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Period revenue
        period_revenue = PaymentHistory.objects.filter(
            created_at__gte=start_date,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Previous period for growth calculation
        previous_period_start = start_date - timedelta(days=days)
        previous_revenue = PaymentHistory.objects.filter(
            created_at__gte=previous_period_start,
            created_at__lt=start_date,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Growth rate
        growth_rate = 0
        if previous_revenue > 0:
            growth_rate = ((period_revenue - previous_revenue) / previous_revenue) * 100
        
        # Revenue by plan
        revenue_by_plan = {}
        for plan in SubscriptionPlan.objects.all():
            plan_revenue = PaymentHistory.objects.filter(
                subscription__plan=plan,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            revenue_by_plan[plan.name] = float(plan_revenue)
        
        # Revenue trend (daily for last 30 days)
        revenue_trend = AnalyticsService._get_revenue_trend(min(days, 30))
        
        # Average order value
        completed_payments = PaymentHistory.objects.filter(status='completed')
        avg_order_value = completed_payments.aggregate(avg=Avg('amount'))['avg'] or 0
        
        return {
            'total_revenue': float(total_revenue),
            'period_revenue': float(period_revenue),
            'revenue_growth_rate': growth_rate,
            'revenue_by_plan': revenue_by_plan,
            'revenue_trend': revenue_trend,
            'average_order_value': float(avg_order_value),
            'period_days': days
        }

    @staticmethod
    def get_usage_analytics(days: int = 30) -> Dict:
        """
        Get usage analytics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with usage analytics
        """
        # Placeholder implementation - will be updated when locator app is available
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        return {
            'total_searches': 0,
            'searches_this_period': 0,
            'average_searches_per_user': 0.0,
            'popular_search_locations': [],
            'usage_by_plan': {},
            'peak_usage_hours': [],
            'period_days': days
        }

    @staticmethod
    def _get_user_growth(days: int) -> List[Dict]:
        """Get user growth data for the last N days."""
        growth_data = []
        end_date = timezone.now().date()
        
        for i in range(days):
            day = end_date - timedelta(days=i)
            day_start = timezone.datetime.combine(day, timezone.datetime.min.time())
            day_end = day_start + timedelta(days=1)
            
            new_users = User.objects.filter(
                date_joined__gte=day_start,
                date_joined__lt=day_end
            ).count()
            
            growth_data.append({
                'date': day.isoformat(),
                'new_users': new_users
            })
        
        return list(reversed(growth_data))

    @staticmethod
    def _get_revenue_trend(days: int) -> List[Dict]:
        """Get revenue trend for the last N days."""
        trend_data = []
        end_date = timezone.now().date()
        
        for i in range(days):
            day = end_date - timedelta(days=i)
            day_start = timezone.datetime.combine(day, timezone.datetime.min.time())
            day_end = day_start + timedelta(days=1)
            
            day_revenue = PaymentHistory.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            trend_data.append({
                'date': day.isoformat(),
                'revenue': float(day_revenue)
            })
        
        return list(reversed(trend_data))

    @staticmethod
    def _get_plan_distribution() -> Dict:
        """Get distribution of users by subscription plan."""
        distribution = {}
        
        # Count users by active subscription plans
        for plan in SubscriptionPlan.objects.all():
            count = UserSubscription.objects.filter(plan=plan, is_active=True).count()
            distribution[plan.name] = count
        
        # Count free users (no subscription)
        free_users = User.objects.filter(subscription__isnull=True).count()
        distribution['NO_SUBSCRIPTION'] = free_users
        
        return distribution

    @staticmethod
    def _get_top_countries(limit: int = 5) -> List[Dict]:
        """Get top countries by user count."""
        # This would use profile data when available
        countries = User.objects.select_related('profile').exclude(
            profile__country__isnull=True
        ).exclude(
            profile__country=''
        ).values('profile__country').annotate(
            user_count=Count('id')
        ).order_by('-user_count')[:limit]
        
        return [
            {
                'country': country['profile__country'],
                'user_count': country['user_count']
            }
            for country in countries
        ]

    @staticmethod
    def get_system_analytics() -> Dict:
        """Get system performance analytics."""
        # Placeholder for system metrics
        return {
            'api_requests_today': 0,
            'error_rate': 0.0,
            'average_response_time': 0.0,
            'system_uptime': 99.9,
            'database_size': "N/A",
            'active_sessions': 0
        }