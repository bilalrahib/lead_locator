from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from typing import Dict, List, Optional
from ..models import CustomUser, UserProfile, UserActivity
import logging

logger = logging.getLogger(__name__)


class UserService:
    """
    Service for user management operations.
    """

    @staticmethod
    def get_user_stats(user: CustomUser) -> Dict:
        """
        Get comprehensive user statistics.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with user statistics
        """
        stats = {
            'account_info': {
                'email': user.email,
                'date_joined': user.date_joined,
                'last_login': user.last_login,
                'last_activity': user.last_activity,
                'account_age_days': (timezone.now() - user.date_joined).days,
                'email_verified': user.email_verified,
                'subscription_status': user.subscription_status,
                'is_premium': user.is_premium_user,
            },
            'activity_stats': UserService._get_activity_stats(user),
            'profile_stats': UserService._get_profile_stats(user),
            'subscription_stats': UserService._get_subscription_stats(user),
        }
        
        return stats

    @staticmethod
    def _get_activity_stats(user: CustomUser) -> Dict:
        """Get user activity statistics."""
        activities = UserActivity.objects.filter(user=user)
        
        # Activity counts by type
        activity_counts = activities.values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Recent activity (last 30 days)
        recent_activities = activities.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        # Login statistics
        logins = activities.filter(activity_type='login')
        login_count = logins.count()
        last_login_activity = logins.first()
        
        return {
            'total_activities': activities.count(),
            'recent_activities_30_days': recent_activities,
            'login_count': login_count,
            'last_login_activity': last_login_activity.created_at if last_login_activity else None,
            'activity_breakdown': list(activity_counts),
        }

    @staticmethod
    def _get_profile_stats(user: CustomUser) -> Dict:
        """Get user profile statistics."""
        try:
            profile = user.profile
            return {
                'profile_exists': True,
                'completion_percentage': profile.completion_percentage,
                'profile_completed': profile.profile_completed,
                'business_type': profile.business_type,
                'years_in_business': profile.years_in_business,
                'number_of_machines': profile.number_of_machines,
            }
        except UserProfile.DoesNotExist:
            return {
                'profile_exists': False,
                'completion_percentage': 0,
                'profile_completed': False,
            }

    @staticmethod
    def _get_subscription_stats(user: CustomUser) -> Dict:
        """Get user subscription statistics."""
        limits = user.get_subscription_limits()
        
        # Get usage statistics (these would come from other apps)
        # For now, return placeholder data
        return {
            'current_plan': limits['plan_name'],
            'searches_limit': limits['searches_per_month'],
            'searches_used': 0,  # Will be updated by locator app
            'script_templates_limit': limits['script_templates'],
            'scripts_generated': 0,  # Will be updated by ai_toolkit app
            'regeneration_allowed': limits['regeneration_allowed'],
        }

    @staticmethod
    def update_user_profile(user: CustomUser, profile_data: Dict) -> UserProfile:
        """
        Update or create user profile.
        
        Args:
            user: User instance
            profile_data: Profile data dictionary
            
        Returns:
            Updated UserProfile instance
        """
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults=profile_data
        )
        
        if not created:
            # Update existing profile
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()
        
        # Check if profile is now complete
        if profile.completion_percentage >= 80:
            profile.mark_completed()
        
        logger.info(f"Profile {'created' if created else 'updated'} for user: {user.email}")
        return profile

    @staticmethod
    def search_users(query: str, page: int = 1, page_size: int = 20) -> Dict:
        """
        Search users by email, name, or username.
        
        Args:
            query: Search query
            page: Page number
            page_size: Number of results per page
            
        Returns:
            Dictionary with search results and pagination info
        """
        queryset = CustomUser.objects.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(company_name__icontains=query)
        ).select_related('profile').order_by('-date_joined')
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'users': page_obj.object_list,
            'total_count': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }

    @staticmethod
    def get_user_activities(user: CustomUser, activity_type: str = None, 
                          page: int = 1, page_size: int = 20) -> Dict:
        """
        Get user activities with pagination.
        
        Args:
            user: User instance
            activity_type: Filter by activity type
            page: Page number
            page_size: Number of results per page
            
        Returns:
            Dictionary with activities and pagination info
        """
        queryset = UserActivity.objects.filter(user=user)
        
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        queryset = queryset.order_by('-created_at')
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'activities': page_obj.object_list,
            'total_count': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }

    @staticmethod
    def deactivate_user(user: CustomUser, reason: str = '', admin_user: CustomUser = None) -> bool:
        """
        Deactivate user account.
        
        Args:
            user: User to deactivate
            reason: Reason for deactivation
            admin_user: Admin performing the action
            
        Returns:
            True if successful
        """
        user.is_active = False
        user.save()
        
        # Log the deactivation
        UserActivity.log_activity(
            user=user,
            activity_type='account_deactivated',
            description=f"Account deactivated. Reason: {reason}",
            metadata={
                'reason': reason,
                'deactivated_by': admin_user.email if admin_user else 'self'
            }
        )
        
        logger.info(f"User account deactivated: {user.email} - Reason: {reason}")
        return True

    @staticmethod
    def reactivate_user(user: CustomUser, admin_user: CustomUser = None) -> bool:
        """
        Reactivate user account.
        
        Args:
            user: User to reactivate
            admin_user: Admin performing the action
            
        Returns:
            True if successful
        """
        user.is_active = True
        user.unlock_account()  # Also unlock if locked
        user.save()
        
        # Log the reactivation
        UserActivity.log_activity(
            user=user,
            activity_type='account_reactivated',
            description="Account reactivated",
            metadata={
                'reactivated_by': admin_user.email if admin_user else 'system'
            }
        )
        
        logger.info(f"User account reactivated: {user.email}")
        return True

    @staticmethod
    def get_user_dashboard_data(user: CustomUser) -> Dict:
        """
        Get dashboard data for user.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with dashboard data
        """
        # Recent activities (last 5)
        recent_activities = UserActivity.objects.filter(
            user=user
        ).order_by('-created_at')[:5]
        
        # Profile completion
        try:
            profile_completion = user.profile.completion_percentage
        except:
            profile_completion = 0
        
        # Quick stats
        stats = {
            'searches_this_month': 0,  # Will be updated by locator app
            'scripts_generated': 0,    # Will be updated by ai_toolkit app
            'support_tickets': 0,      # Will be updated by project_core app
        }
        
        return {
            'user_info': {
                'full_name': user.full_name,
                'email': user.email,
                'subscription_status': user.subscription_status,
                'email_verified': user.email_verified,
                'profile_completion': profile_completion,
            },
            'recent_activities': recent_activities,
            'quick_stats': stats,
            'subscription_limits': user.get_subscription_limits(),
        }

    @staticmethod
    def bulk_update_users(user_ids: List[str], update_data: Dict, admin_user: CustomUser = None) -> Dict:
        """
        Bulk update multiple users.
        
        Args:
            user_ids: List of user IDs
            update_data: Data to update
            admin_user: Admin performing the action
            
        Returns:
            Dictionary with update results
        """
        users = CustomUser.objects.filter(id__in=user_ids)
        updated_count = 0
        errors = []
        
        for user in users:
            try:
                for field, value in update_data.items():
                    if hasattr(user, field):
                        setattr(user, field, value)
                user.save()
                
                # Log the update
                UserActivity.log_activity(
                    user=user,
                    activity_type='profile_update',
                    description="Bulk profile update",
                    metadata={
                        'updated_fields': list(update_data.keys()),
                        'updated_by': admin_user.email if admin_user else 'system'
                    }
                )
                
                updated_count += 1
                
            except Exception as e:
                errors.append(f"Error updating user {user.email}: {str(e)}")
        
        return {
            'updated_count': updated_count,
            'total_count': len(user_ids),
            'errors': errors,
        }