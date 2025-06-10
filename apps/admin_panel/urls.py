from django.urls import path, include
from . import views

app_name = 'admin_panel'

# API URL patterns
api_patterns = [
    # Dashboard
    path('dashboard/', views.AdminDashboardAPIView.as_view(), name='api_dashboard'),
    path('stats/', views.get_admin_stats, name='api_stats'),
    
    # User Management
    path('users/', views.AdminUserListAPIView.as_view(), name='api_users'),
    path('users/<uuid:id>/', views.AdminUserDetailAPIView.as_view(), name='api_user_detail'),
    path('users/activate/', views.UserActivationAPIView.as_view(), name='api_user_activation'),
    path('users/change-subscription/', views.UserSubscriptionChangeAPIView.as_view(), name='api_user_subscription_change'),
    path('users/bulk-action/', views.BulkUserActionAPIView.as_view(), name='api_bulk_user_action'),
    
    # Analytics
    path('analytics/', views.AnalyticsDashboardAPIView.as_view(), name='api_analytics_dashboard'),
    path('analytics/users/', views.UserAnalyticsAPIView.as_view(), name='api_user_analytics'),
    path('analytics/revenue/', views.RevenueAnalyticsAPIView.as_view(), name='api_revenue_analytics'),
    path('analytics/subscriptions/', views.SubscriptionAnalyticsAPIView.as_view(), name='api_subscription_analytics'),
    
    # Subscription Management
    path('subscription-plans/', views.AdminSubscriptionPlansAPIView.as_view(), name='api_subscription_plans'),
    path('lead-packages/', views.AdminLeadPackagesAPIView.as_view(), name='api_lead_packages'),
    
    # Content Management
    path('templates/', views.ContentTemplateListCreateAPIView.as_view(), name='api_templates'),
    path('templates/<uuid:pk>/', views.ContentTemplateDetailAPIView.as_view(), name='api_template_detail'),
    
    # System Settings
    path('settings/', views.SystemSettingsAPIView.as_view(), name='api_settings'),
    path('settings/<int:pk>/', views.SystemSettingUpdateAPIView.as_view(), name='api_setting_update'),
    
    # Admin Logs
    path('logs/', views.AdminLogListAPIView.as_view(), name='api_logs'),
    
    # Health Check
    path('health/', views.admin_panel_health_check, name='api_health'),
]

urlpatterns = [
    # API endpoints
    path('api/v1/admin/', include(api_patterns)),
]