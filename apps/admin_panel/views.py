from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Q
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from apps.project_core.utils.helpers import get_client_ip
from django.utils import timezone
import logging

from .models import AdminLog, ContentTemplate, SystemSettings, AdminDashboardStats
from .permissions import (
    IsAdminUser, IsSuperUser, CanManageUsers, CanManageSubscriptions,
    CanViewAnalytics, CanManageContent
)
from .serializers import (
    AdminUserListSerializer, AdminUserDetailSerializer, UserActivationSerializer,
    UserSubscriptionChangeSerializer, BulkUserActionSerializer,
    AdminSubscriptionPlanSerializer, AdminLeadCreditPackageSerializer,
    SubscriptionAnalyticsSerializer, DashboardStatsSerializer,
    UserAnalyticsSerializer, RevenueAnalyticsSerializer, UsageAnalyticsSerializer,
    ContentTemplateSerializer, ContentTemplateCreateSerializer,
    SystemSettingsSerializer, AdminLogSerializer
)
from .services import UserAdminService, AnalyticsService, SubscriptionAdminService, ContentManagementService

User = get_user_model()
logger = logging.getLogger(__name__)


# Dashboard Views
class AdminDashboardAPIView(APIView):
    """
    API endpoint for admin dashboard overview.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Get dashboard statistics and overview."""
        try:
            force_refresh = request.query_params.get('refresh', 'false').lower() == 'true'
            
            # Get dashboard stats
            dashboard_stats = AnalyticsService.get_dashboard_stats(force_refresh)
            
            # Get quick user stats
            user_stats = UserAdminService.get_user_statistics()
            
            # Get subscription overview
            subscription_stats = SubscriptionAdminService.get_subscription_analytics(30)
            
            return Response({
                'dashboard_stats': dashboard_stats,
                'user_overview': user_stats,
                'subscription_overview': subscription_stats,
                'quick_actions': {
                    'pending_support_tickets': dashboard_stats.get('support_tickets_open', 0),
                    'new_users_today': dashboard_stats.get('new_users_today', 0),
                    'revenue_today': dashboard_stats.get('revenue_today', 0)
                }
            })
            
        except Exception as e:
            logger.error(f"Error in admin dashboard: {e}")
            return Response({
                'error': 'Unable to load dashboard data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# User Management Views
class AdminUserListAPIView(generics.ListAPIView):
    """
    API endpoint for listing users in admin panel.
    """
    serializer_class = AdminUserListSerializer
    permission_classes = [CanManageUsers]

    def get_queryset(self):
        queryset = User.objects.select_related('subscription__plan', 'profile')
        
        # Apply filters
        search = self.request.query_params.get('search')
        plan = self.request.query_params.get('plan')
        status_filter = self.request.query_params.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(company_name__icontains=search)
            )
        
        if plan and plan != 'all':
            if plan == 'free':
                queryset = queryset.filter(
                    Q(subscription__isnull=True) |
                    Q(subscription__plan__name='FREE')
                )
            else:
                queryset = queryset.filter(subscription__plan__name=plan)
        
        if status_filter and status_filter != 'all':
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
            elif status_filter == 'verified':
                queryset = queryset.filter(email_verified=True)
            elif status_filter == 'unverified':
                queryset = queryset.filter(email_verified=False)
        
        return queryset.order_by('-date_joined')


class AdminUserDetailAPIView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for user details in admin panel.
    """
    serializer_class = AdminUserDetailSerializer
    permission_classes = [CanManageUsers]
    lookup_field = 'id'

    def get_queryset(self):
        return User.objects.select_related('subscription__plan', 'profile')

    def perform_update(self, serializer):
        user = serializer.save()
        
        # Log admin action
        AdminLog.objects.create(
            admin_user=self.request.user,
            action_type='user_update',
            target_user=user,
            description=f"User profile updated via admin panel",
            ip_address=get_client_ip(self.request)
        )


class UserActivationAPIView(APIView):
    """
    API endpoint for activating/deactivating users.
    """
    permission_classes = [CanManageUsers]

    def post(self, request):
        """Activate or deactivate users."""
        serializer = UserActivationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_ids = serializer.validated_data['user_ids']
        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')

        try:
            if action == 'activate':
                result = UserAdminService.activate_users(user_ids, request.user, reason)
            else:
                result = UserAdminService.deactivate_users(user_ids, request.user, reason)
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error in user activation: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSubscriptionChangeAPIView(APIView):
    """
    API endpoint for changing user subscriptions.
    """
    permission_classes = [CanManageSubscriptions]

    def post(self, request):
        """Change user subscription plan."""
        serializer = UserSubscriptionChangeSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = UserAdminService.change_user_subscription(
                user_id=serializer.validated_data['user_id'],
                new_plan_id=serializer.validated_data['new_plan_id'],
                admin_user=request.user,
                reason=serializer.validated_data.get('reason', ''),
                effective_immediately=serializer.validated_data.get('effective_immediately', True)
            )
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error changing user subscription: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BulkUserActionAPIView(APIView):
    """
    API endpoint for bulk user operations.
    """
    permission_classes = [CanManageUsers]

    def post(self, request):
        """Perform bulk actions on users."""
        serializer = BulkUserActionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_ids = serializer.validated_data['user_ids']
        action = serializer.validated_data['action']
        parameters = serializer.validated_data.get('parameters', {})

        try:
            if action == 'activate':
                result = UserAdminService.activate_users(user_ids, request.user)
            elif action == 'deactivate':
                result = UserAdminService.deactivate_users(user_ids, request.user)
            elif action == 'grant_credits':
                result = UserAdminService.grant_lead_credits(
                    user_ids, parameters['package_id'], request.user
                )
            elif action == 'verify_email':
                # Implement email verification logic
                users = User.objects.filter(id__in=user_ids)
                for user in users:
                    user.email_verified = True
                    user.save(update_fields=['email_verified'])
                result = {'updated_count': users.count(), 'message': 'Emails verified'}
            elif action == 'unlock_account':
                # Implement account unlock logic
                users = User.objects.filter(id__in=user_ids)
                for user in users:
                    user.unlock_account()
                result = {'updated_count': users.count(), 'message': 'Accounts unlocked'}
            else:
                return Response({
                    'error': f'Unsupported action: {action}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error in bulk user action: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Analytics Views
class AnalyticsDashboardAPIView(APIView):
    """
    API endpoint for analytics dashboard.
    """
    permission_classes = [CanViewAnalytics]

    def get(self, request):
        """Get comprehensive analytics data."""
        try:
            days = int(request.query_params.get('days', 30))
            
            # Get different types of analytics
            user_analytics = AnalyticsService.get_user_analytics(days)
            revenue_analytics = AnalyticsService.get_revenue_analytics(days)
            usage_analytics = AnalyticsService.get_usage_analytics(days)
            system_analytics = AnalyticsService.get_system_analytics()
            
            return Response({
                'user_analytics': user_analytics,
                'revenue_analytics': revenue_analytics,
                'usage_analytics': usage_analytics,
                'system_analytics': system_analytics,
                'period_days': days
            })
            
        except Exception as e:
            logger.error(f"Error in analytics dashboard: {e}")
            return Response({
                'error': 'Unable to load analytics data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserAnalyticsAPIView(APIView):
    """
    API endpoint for user analytics.
    """
    permission_classes = [CanViewAnalytics]

    def get(self, request):
        """Get detailed user analytics."""
        try:
            days = int(request.query_params.get('days', 30))
            analytics = AnalyticsService.get_user_analytics(days)
            
            serializer = UserAnalyticsSerializer(analytics)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in user analytics: {e}")
            return Response({
                'error': 'Unable to load user analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RevenueAnalyticsAPIView(APIView):
    """
    API endpoint for revenue analytics.
    """
    permission_classes = [CanViewAnalytics]

    def get(self, request):
        """Get detailed revenue analytics."""
        try:
            days = int(request.query_params.get('days', 30))
            analytics = AnalyticsService.get_revenue_analytics(days)
            
            serializer = RevenueAnalyticsSerializer(analytics)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in revenue analytics: {e}")
            return Response({
                'error': 'Unable to load revenue analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Subscription Management Views
class AdminSubscriptionPlansAPIView(generics.ListCreateAPIView):
    """
    API endpoint for managing subscription plans.
    """
    serializer_class = AdminSubscriptionPlanSerializer
    permission_classes = [CanManageSubscriptions]

    def get_queryset(self):
        from apps.project_core.models import SubscriptionPlan
        return SubscriptionPlan.objects.all().order_by('price')

    def perform_create(self, serializer):
        plan = serializer.save()
        
        # Log action
        AdminLog.objects.create(
            admin_user=self.request.user,
            action_type='subscription_plan_create',
            description=f"Created subscription plan: {plan.name}",
            after_state={'plan_name': plan.name, 'price': float(plan.price)}
        )


class AdminLeadPackagesAPIView(generics.ListCreateAPIView):
    """
    API endpoint for managing lead credit packages.
    """
    serializer_class = AdminLeadCreditPackageSerializer
    permission_classes = [CanManageSubscriptions]

    def get_queryset(self):
        from apps.subscriptions.models import LeadCreditPackage
        return LeadCreditPackage.objects.all().order_by('price')

    def perform_create(self, serializer):
        package = serializer.save()
        
        # Log action
        AdminLog.objects.create(
            admin_user=self.request.user,
            action_type='lead_package_create',
            description=f"Created lead package: {package.name}",
            after_state={'package_name': package.name, 'price': float(package.price)}
        )


class SubscriptionAnalyticsAPIView(APIView):
    """
    API endpoint for subscription analytics.
    """
    permission_classes = [CanViewAnalytics]

    def get(self, request):
        """Get subscription analytics."""
        try:
            days = int(request.query_params.get('days', 30))
            analytics = SubscriptionAdminService.get_subscription_analytics(days)
            
            serializer = SubscriptionAnalyticsSerializer(analytics)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in subscription analytics: {e}")
            return Response({
                'error': 'Unable to load subscription analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Content Management Views
class ContentTemplateListCreateAPIView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating content templates.
    """
    permission_classes = [CanManageContent]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ContentTemplateCreateSerializer
        return ContentTemplateSerializer

    def get_queryset(self):
        queryset = ContentTemplate.objects.select_related('created_by')
        
        # Apply filters
        template_type = self.request.query_params.get('type')
        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        
        if template_type:
            queryset = queryset.filter(template_type=template_type)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        template = serializer.save()
        
        # Log action
        AdminLog.objects.create(
            admin_user=self.request.user,
            action_type='content_create',
            description=f"Created template: {template.name}",
            after_state={'template_name': template.name, 'type': template.template_type}
        )


class ContentTemplateDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for managing individual content templates.
    """
    serializer_class = ContentTemplateSerializer
    permission_classes = [CanManageContent]
    queryset = ContentTemplate.objects.all()

    def perform_update(self, serializer):
        template = serializer.save()
        
        # Log action
        AdminLog.objects.create(
            admin_user=self.request.user,
            action_type='content_update',
            description=f"Updated template: {template.name}",
            after_state={'template_name': template.name}
        )

    def perform_destroy(self, instance):
        template_name = instance.name
        instance.delete()
        
        # Log action
        AdminLog.objects.create(
            admin_user=self.request.user,
            action_type='content_delete',
            description=f"Deleted template: {template_name}",
            before_state={'template_name': template_name}
        )


class SystemSettingsAPIView(generics.ListAPIView):
    """
    API endpoint for viewing system settings.
    """
    serializer_class = SystemSettingsSerializer
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        category = self.request.query_params.get('category')
        queryset = SystemSettings.objects.filter(is_active=True)
        
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset.order_by('category', 'key')


class SystemSettingUpdateAPIView(APIView):
    """
    API endpoint for updating individual system settings.
    """
    permission_classes = [IsSuperUser]

    def patch(self, request, pk):
        """Update a system setting."""
        try:
            setting = SystemSettings.objects.get(id=pk, is_editable=True)
            new_value = request.data.get('value')
            
            if new_value is None:
                return Response({
                    'error': 'Value is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            old_value = setting.value
            setting.value = str(new_value)
            setting.updated_by = request.user
            setting.save()
            
            # Log action
            AdminLog.objects.create(
                admin_user=request.user,
                action_type='system_setting',
                description=f"Updated setting: {setting.key}",
                before_state={'value': old_value},
                after_state={'value': setting.value}
            )
            
            serializer = SystemSettingsSerializer(setting)
            return Response(serializer.data)
            
        except SystemSettings.DoesNotExist:
            return Response({
                'error': 'Setting not found or not editable'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating system setting: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Admin Logs Views
class AdminLogListAPIView(generics.ListAPIView):
    """
    API endpoint for viewing admin activity logs.
    """
    serializer_class = AdminLogSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = AdminLog.objects.select_related('admin_user', 'target_user')
        
        # Apply filters
        action_type = self.request.query_params.get('action_type')
        admin_user = self.request.query_params.get('admin_user')
        target_user = self.request.query_params.get('target_user')
        
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        if admin_user:
            queryset = queryset.filter(admin_user__id=admin_user)
        
        if target_user:
            queryset = queryset.filter(target_user__id=target_user)
        
        return queryset.order_by('-created_at')


# Health Check and Utility Views
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_panel_health_check(request):
    """
    Health check for admin panel.
    """
    try:
        # Test database connections
        user_count = User.objects.count()
        admin_count = User.objects.filter(is_staff=True).count()
        log_count = AdminLog.objects.count()
        
        return Response({
            'status': 'healthy',
            'total_users': user_count,
            'admin_users': admin_count,
            'admin_logs': log_count,
            'app': 'admin_panel'
        })
        
    except Exception as e:
        logger.error(f"Admin panel health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'app': 'admin_panel'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_admin_stats(request):
    """
    Get quick admin statistics.
    """
    try:
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'verified_users': User.objects.filter(email_verified=True).count(),
            'total_templates': ContentTemplate.objects.count(),
            'active_templates': ContentTemplate.objects.filter(status='active').count(),
            'admin_actions_today': AdminLog.objects.filter(
                created_at__date=timezone.now().date()
            ).count()
        }
        
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        return Response({
            'error': 'Unable to load statistics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)