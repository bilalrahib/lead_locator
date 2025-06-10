from django.urls import path, include
from . import views

app_name = 'project_core'

# API URL patterns (no separate namespace)
api_patterns = [
    path('homepage/', views.HomepageDataAPIView.as_view(), name='api_homepage_data'),
    path('contact/', views.ContactMessageCreateAPIView.as_view(), name='api_contact_create'),
    path('support-tickets/', views.SupportTicketListCreateAPIView.as_view(), name='api_support_tickets'),
    path('support-tickets/<uuid:pk>/', views.SupportTicketDetailAPIView.as_view(), name='api_support_ticket_detail'),
    path('weather-location/', views.WeatherLocationAPIView.as_view(), name='api_weather_location'),
    path('weather/', views.get_weather_data, name='api_weather_data'),
    path('notifications/', views.SystemNotificationListAPIView.as_view(), name='api_notifications'),
    path('health/', views.health_check, name='api_health_check'),
    path('status/', views.system_status, name='api_system_status'),
]

# Web URL patterns (no separate namespace)
web_patterns = [
    path('', views.HomepageView.as_view(), name='homepage'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]

urlpatterns = [
    # API endpoints with api/ prefix
    path('api/v1/core/', include(api_patterns)),
    # Web pages at root level
] + web_patterns