from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List
import logging

from apps.project_core.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.models import LeadCreditPackage, PaymentHistory
from ..models import AdminLog

logger = logging.getLogger(__name__)


class SubscriptionAdminService:
    """Service for subscription management in admin panel."""

    @staticmethod
    def get_subscription_analytics(days: int = 30) -> Dict:
        """
        Get subscription analytics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with subscription analytics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Basic subscription counts
        total_subscriptions = UserSubscription.objects.count()
        active_subscriptions = UserSubscription.objects.filter(is_active=True).count()
        
        # Plan distribution
        plan_distribution = {}
        for plan in SubscriptionPlan.objects.all():
            count = UserSubscription.objects.filter(plan=plan, is_active=True).count()
            plan_distribution[plan.name] = count
        
        # Revenue metrics
        period_revenue = PaymentHistory.objects.filter(
            created_at__gte=start_date,
            subscription__isnull=False,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate churn rate (cancelled subscriptions in period)
        cancelled_subscriptions = UserSubscription.objects.filter(
            end_date__gte=start_date,
            is_active=False
        ).count()
        
        churn_rate = 0
        if total_subscriptions > 0:
            churn_rate = (cancelled_subscriptions / total_subscriptions) * 100
        
        # Calculate upgrade rate (subscription changes in period)
        from apps.subscriptions.models import SubscriptionUpgradeRequest
        upgrades = SubscriptionUpgradeRequest.objects.filter(
            created_at__gte=start_date,
            status='completed'
        ).count()
        
        upgrade_rate = 0
        if active_subscriptions > 0:
            upgrade_rate = (upgrades / active_subscriptions) * 100
        
        # Calculate ARPU (Average Revenue Per User)
        arpu = 0
        if active_subscriptions > 0:
            arpu = period_revenue / active_subscriptions
        
        # Subscription growth over time
        subscription_growth = SubscriptionAdminService._get_subscription_growth(days)
        
        return {
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'plan_distribution': plan_distribution,
            'monthly_revenue': float(period_revenue),
            'churn_rate': churn_rate,
            'upgrade_rate': upgrade_rate,
            'average_revenue_per_user': float(arpu),
            'subscription_growth': subscription_growth,
            'period_days': days
        }

    @staticmethod
    def get_plan_performance() -> List[Dict]:
        """
        Get performance metrics for each subscription plan.
        
        Returns:
            List of plan performance data
        """
        plan_performance = []
        
        for plan in SubscriptionPlan.objects.all():
            # Count active subscriptions
            active_count = UserSubscription.objects.filter(
                plan=plan,
                is_active=True
            ).count()
            
            # Calculate revenue
            total_revenue = PaymentHistory.objects.filter(
                subscription__plan=plan,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate monthly revenue (approximate)
            monthly_revenue = total_revenue  # This could be refined with proper date filtering
            
            # Calculate conversion rate (new subscriptions in last 30 days)
            last_30_days = timezone.now() - timedelta(days=30)
            new_subscriptions = UserSubscription.objects.filter(
                plan=plan,
                created_at__gte=last_30_days
            ).count()
            
            plan_performance.append({
                'plan_id': plan.id,
                'plan_name': plan.name,
                'plan_price': float(plan.price),
                'active_subscribers': active_count,
                'total_revenue': float(total_revenue),
                'monthly_revenue': float(monthly_revenue),
                'new_subscriptions_30_days': new_subscriptions,
                'leads_per_month': plan.leads_per_month,
                'is_active': plan.is_active
            })
        
        return sorted(plan_performance, key=lambda x: x['active_subscribers'], reverse=True)

    @staticmethod
    def get_package_performance() -> List[Dict]:
        """
        Get performance metrics for lead credit packages.
        
        Returns:
            List of package performance data
        """
        package_performance = []
        
        for package in LeadCreditPackage.objects.all():
            # Count purchases
            purchase_count = PaymentHistory.objects.filter(
                package_purchased=package,
                status='completed'
            ).count()
            
            # Calculate revenue
            total_revenue = PaymentHistory.objects.filter(
                package_purchased=package,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate credits distributed
            from apps.subscriptions.models import UserLeadCredit
            total_credits = UserLeadCredit.objects.filter(
                package=package
            ).aggregate(total=Sum('credits_purchased'))['total'] or 0
            
            package_performance.append({
                'package_id': str(package.id),
                'package_name': package.name,
                'package_price': float(package.price),
                'lead_count': package.lead_count,
                'purchase_count': purchase_count,
                'total_revenue': float(total_revenue),
                'total_credits_distributed': total_credits,
                'price_per_lead': float(package.price_per_lead),
                'is_active': package.is_active
            })
        
        return sorted(package_performance, key=lambda x: x['purchase_count'], reverse=True)

    @staticmethod
    def _get_subscription_growth(days: int) -> List[Dict]:
        """Get subscription growth data over time."""
        growth_data = []
        end_date = timezone.now().date()
        
        for i in range(min(days, 30)):  # Limit to 30 days for performance
            day = end_date - timedelta(days=i)
            day_start = timezone.datetime.combine(day, timezone.datetime.min.time())
            day_end = day_start + timedelta(days=1)
            
            new_subscriptions = UserSubscription.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).count()
            
            cancelled_subscriptions = UserSubscription.objects.filter(
                end_date__gte=day_start,
                end_date__lt=day_end,
                is_active=False
            ).count()
            
            growth_data.append({
                'date': day.isoformat(),
                'new_subscriptions': new_subscriptions,
                'cancelled_subscriptions': cancelled_subscriptions,
                'net_growth': new_subscriptions - cancelled_subscriptions
            })
        
        return list(reversed(growth_data))

    @staticmethod
    def create_subscription_plan(plan_data: Dict, admin_user) -> Dict:
        """
        Create a new subscription plan.
        
        Args:
            plan_data: Plan configuration data
            admin_user: Admin creating the plan
            
        Returns:
            Dict with creation results
        """
        try:
            plan = SubscriptionPlan.objects.create(**plan_data)
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='subscription_plan_create',
                description=f"Created subscription plan: {plan.name}",
                after_state=plan_data
            )
            
            logger.info(f"Subscription plan {plan.name} created by {admin_user.email}")
            
            return {
                'success': True,
                'plan_id': plan.id,
                'message': f"Successfully created plan {plan.name}"
            }
            
        except Exception as e:
            logger.error(f"Error creating subscription plan: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_lead_package(package_data: Dict, admin_user) -> Dict:
        """
        Create a new lead credit package.
        
        Args:
            package_data: Package configuration data
            admin_user: Admin creating the package
            
        Returns:
            Dict with creation results
        """
        try:
            package = LeadCreditPackage.objects.create(**package_data)
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='lead_package_create',
                description=f"Created lead package: {package.name}",
                after_state=package_data
            )
            
            logger.info(f"Lead package {package.name} created by {admin_user.email}")
            
            return {
                'success': True,
                'package_id': str(package.id),
                'message': f"Successfully created package {package.name}"
            }
            
        except Exception as e:
            logger.error(f"Error creating lead package: {e}")
            return {
                'success': False,
                'error': str(e)
            }