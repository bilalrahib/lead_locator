from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Count, Avg
from typing import Dict, List, Optional
from datetime import timedelta
import logging
try:
    from apps.project_core.models import SubscriptionPlan, UserSubscription
except ImportError:
    # Handle case where these models might not exist yet
    SubscriptionPlan = None
    UserSubscription = None

#from apps.project_core.models import SubscriptionPlan, UserSubscription
try:
    from apps.subscriptions.models import LeadCreditPackage, UserLeadCredit, PaymentHistory
except ImportError:
    # Handle case where these models might not exist yet
    LeadCreditPackage = None
    UserLeadCredit = None
    PaymentHistory = None

#from apps.subscriptions.models import LeadCreditPackage, UserLeadCredit, PaymentHistory
from ..models import AdminLog

User = get_user_model()
logger = logging.getLogger(__name__)


class UserAdminService:
    """Service for user management operations in admin panel."""

    @staticmethod
    def get_user_list(search: str = None, plan: str = None, status: str = None, 
                     page: int = 1, page_size: int = 20) -> Dict:
        """
        Get paginated list of users with filters.
        
        Args:
            search: Search query for email/name
            plan: Filter by subscription plan
            status: Filter by user status
            page: Page number
            page_size: Results per page
            
        Returns:
            Dict with user list and pagination info
        """
        queryset = User.objects.select_related('subscription__plan', 'profile')
        
        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        if plan:
            if plan == 'free':
                queryset = queryset.filter(
                    Q(subscription__isnull=True) |
                    Q(subscription__plan__name='FREE')
                )
            else:
                queryset = queryset.filter(subscription__plan__name=plan)
        
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'verified':
            queryset = queryset.filter(email_verified=True)
        elif status == 'unverified':
            queryset = queryset.filter(email_verified=False)
        
        # Count total
        total_count = queryset.count()
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        users = queryset[start:end]
        
        return {
            'users': users,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }

    @staticmethod
    @transaction.atomic
    def activate_users(user_ids: List[str], admin_user: User, reason: str = "") -> Dict:
        """
        Activate multiple users.
        
        Args:
            user_ids: List of user IDs to activate
            admin_user: Admin performing the action
            reason: Reason for activation
            
        Returns:
            Dict with operation results
        """
        users = User.objects.filter(id__in=user_ids, is_active=False)
        updated_count = 0
        
        for user in users:
            old_status = user.is_active
            user.is_active = True
            user.save(update_fields=['is_active'])
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='user_activate',
                target_user=user,
                description=f"User activated. Reason: {reason}",
                before_state={'is_active': old_status},
                after_state={'is_active': True}
            )
            
            updated_count += 1
            logger.info(f"User {user.email} activated by {admin_user.email}")
        
        return {
            'updated_count': updated_count,
            'total_requested': len(user_ids),
            'message': f"Successfully activated {updated_count} users"
        }

    @staticmethod
    @transaction.atomic
    def deactivate_users(user_ids: List[str], admin_user: User, reason: str = "") -> Dict:
        """
        Deactivate multiple users.
        
        Args:
            user_ids: List of user IDs to deactivate
            admin_user: Admin performing the action
            reason: Reason for deactivation
            
        Returns:
            Dict with operation results
        """
        users = User.objects.filter(id__in=user_ids, is_active=True)
        updated_count = 0
        
        for user in users:
            # Don't allow deactivating superusers
            if user.is_superuser:
                continue
                
            old_status = user.is_active
            user.is_active = False
            user.save(update_fields=['is_active'])
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='user_deactivate',
                target_user=user,
                description=f"User deactivated. Reason: {reason}",
                before_state={'is_active': old_status},
                after_state={'is_active': False}
            )
            
            updated_count += 1
            logger.info(f"User {user.email} deactivated by {admin_user.email}")
        
        return {
            'updated_count': updated_count,
            'total_requested': len(user_ids),
            'message': f"Successfully deactivated {updated_count} users"
        }

    @staticmethod
    @transaction.atomic
    def change_user_subscription(user_id: str, new_plan_id: int, admin_user: User,
                               reason: str = "", effective_immediately: bool = True) -> Dict:
        """
        Change user's subscription plan.
        
        Args:
            user_id: User ID
            new_plan_id: New subscription plan ID
            admin_user: Admin performing the action
            reason: Reason for change
            effective_immediately: Whether to apply immediately
            
        Returns:
            Dict with operation results
        """
        try:
            user = User.objects.get(id=user_id)
            new_plan = SubscriptionPlan.objects.get(id=new_plan_id, is_active=True)
            
            old_subscription = None
            old_plan_name = "None"
            
            if hasattr(user, 'subscription') and user.subscription:
                old_subscription = user.subscription
                old_plan_name = old_subscription.plan.name
            
            # Create new subscription
            if old_subscription:
                # Update existing subscription
                old_subscription.plan = new_plan
                old_subscription.save()
                new_subscription = old_subscription
            else:
                # Create new subscription
                new_subscription = UserSubscription.objects.create(
                    user=user,
                    plan=new_plan,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=30),
                    is_active=True
                )
                user.current_subscription = new_subscription
                user.save(update_fields=['current_subscription'])
            
            # Log action
            AdminLog.objects.create(
                admin_user=admin_user,
                action_type='subscription_change',
                target_user=user,
                description=f"Subscription changed from {old_plan_name} to {new_plan.name}. Reason: {reason}",
                before_state={'plan': old_plan_name},
                after_state={'plan': new_plan.name}
            )
            
            logger.info(f"User {user.email} subscription changed to {new_plan.name} by {admin_user.email}")
            
            return {
                'success': True,
                'message': f"Successfully changed subscription to {new_plan.name}",
                'new_plan': new_plan.name
            }
            
        except User.DoesNotExist:
            return {'success': False, 'error': 'User not found'}
        except SubscriptionPlan.DoesNotExist:
            return {'success': False, 'error': 'Subscription plan not found'}
        except Exception as e:
            logger.error(f"Error changing user subscription: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    @transaction.atomic
    def grant_lead_credits(user_ids: List[str], package_id: str, admin_user: User,
                          reason: str = "") -> Dict:
        """
        Grant lead credits to multiple users.
        
        Args:
            user_ids: List of user IDs
            package_id: Lead credit package ID
            admin_user: Admin performing the action
            reason: Reason for granting credits
            
        Returns:
            Dict with operation results
        """
        try:
            package = LeadCreditPackage.objects.get(id=package_id)
            users = User.objects.filter(id__in=user_ids)
            granted_count = 0
            
            for user in users:
                # Create a dummy payment record for the grant
                payment = PaymentHistory.objects.create(
                    user=user,
                    package_purchased=package,
                    amount=0,  # Free grant
                    payment_gateway='manual',
                    transaction_id=f"admin_grant_{user.id}_{int(timezone.now().timestamp())}",
                    status='completed'
                )
                
                # Create lead credit
                UserLeadCredit.objects.create(
                    user=user,
                    package=package,
                    payment=payment,
                    credits_purchased=package.lead_count,
                    expires_at=timezone.now() + timedelta(days=365)
                )
                
                # Log action
                AdminLog.objects.create(
                    admin_user=admin_user,
                    action_type='credit_grant',
                    target_user=user,
                    description=f"Granted {package.lead_count} credits from {package.name}. Reason: {reason}",
                    after_state={
                        'package': package.name,
                        'credits': package.lead_count
                    }
                )
                
                granted_count += 1
                logger.info(f"Granted {package.lead_count} credits to {user.email} by {admin_user.email}")
            
            return {
                'granted_count': granted_count,
                'total_requested': len(user_ids),
                'message': f"Successfully granted credits to {granted_count} users"
            }
            
        except LeadCreditPackage.DoesNotExist:
            return {'success': False, 'error': 'Package not found'}
        except Exception as e:
            logger.error(f"Error granting credits: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_user_statistics() -> Dict:
        """
        Get overall user statistics.
        
        Returns:
            Dict with user statistics
        """
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        verified_users = User.objects.filter(email_verified=True).count()
        
        # Users by plan
        plan_distribution = {}
        for plan in SubscriptionPlan.objects.all():
            count = UserSubscription.objects.filter(plan=plan, is_active=True).count()
            plan_distribution[plan.name] = count
        
        # Free users (no subscription or free plan)
        free_users = User.objects.filter(
            Q(subscription__isnull=True) |
            Q(subscription__plan__name='FREE')
        ).count()
        plan_distribution['FREE'] = free_users
        
        # Recent registrations
        last_30_days = timezone.now() - timedelta(days=30)
        new_users_30_days = User.objects.filter(date_joined__gte=last_30_days).count()
        
        # User retention (active in last 30 days)
        active_30_days = User.objects.filter(last_activity__gte=last_30_days).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'verified_users': verified_users,
            'verification_rate': (verified_users / total_users * 100) if total_users > 0 else 0,
            'plan_distribution': plan_distribution,
            'new_users_30_days': new_users_30_days,
            'active_users_30_days': active_30_days,
            'retention_rate': (active_30_days / total_users * 100) if total_users > 0 else 0
        }