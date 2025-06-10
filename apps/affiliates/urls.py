from django.urls import path, include
from . import views

app_name = 'affiliates'

# API URL patterns
api_patterns = [
    # Affiliate Management
    path('apply/', views.AffiliateApplicationView.as_view(), name='api_apply'),
    path('dashboard/', views.AffiliateDashboardView.as_view(), name='api_dashboard'),
    path('profile/', views.AffiliateProfileView.as_view(), name='api_profile'),
    path('payout-info/', views.PayoutInfoView.as_view(), name='api_payout_info'),
    
    # Commission & Earnings
    path('commissions/', views.CommissionHistoryView.as_view(), name='api_commissions'),
    
    # Resources & Tools
    path('resources/', views.AffiliateResourcesView.as_view(), name='api_resources'),
    path('resources/<uuid:resource_id>/download/', views.download_resource, name='api_download_resource'),
    
    # Analytics & Performance
    path('analytics/', views.affiliate_analytics, name='api_analytics'),
    
    # Public Endpoints
    path('leaderboard/', views.affiliate_leaderboard, name='api_leaderboard'),
    
    # Health Check
    path('health/', views.affiliate_health_check, name='api_health'),
]

urlpatterns = [
    # API endpoints
    path('api/v1/affiliates/', include(api_patterns)),
]