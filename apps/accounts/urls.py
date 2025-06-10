from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'accounts'

# API URL patterns
api_patterns = [
    # Authentication
    path('register/', views.UserRegistrationAPIView.as_view(), name='api_register'),
    path('login/', views.UserLoginAPIView.as_view(), name='api_login'),
    path('logout/', views.UserLogoutAPIView.as_view(), name='api_logout'),
    
    # Profile Management
    path('profile/', views.UserProfileAPIView.as_view(), name='api_profile'),
    path('profile/details/', views.UserProfileDetailAPIView.as_view(), name='api_profile_details'),
    path('dashboard/', views.UserDashboardAPIView.as_view(), name='api_dashboard'),
    path('stats/', views.UserStatsAPIView.as_view(), name='api_stats'),
    
    # Password Management
    path('password/change/', views.PasswordChangeAPIView.as_view(), name='api_password_change'),
    path('password/reset/', views.PasswordResetRequestAPIView.as_view(), name='api_password_reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmAPIView.as_view(), name='api_password_reset_confirm'),
    
    # Email Management
    path('email/verify/', views.EmailVerificationAPIView.as_view(), name='api_email_verify'),
    path('email/verify/resend/', views.EmailVerificationResendAPIView.as_view(), name='api_email_verify_resend'),
    path('email/change/', views.EmailChangeAPIView.as_view(), name='api_email_change'),
    
    # Activity and Security
    path('activities/', views.UserActivityListAPIView.as_view(), name='api_activities'),
    path('security/', views.AccountSecurityAPIView.as_view(), name='api_security'),
    
    # Account Management
    path('delete/', views.UserDeleteAPIView.as_view(), name='api_delete'),
    
    # Admin endpoints
    path('search/', views.UserSearchAPIView.as_view(), name='api_search'),
    
    # Health check
    path('health/', views.accounts_health_check, name='api_health'),
]

urlpatterns = [
    # API endpoints
    path('api/v1/accounts/', include(api_patterns)),
]