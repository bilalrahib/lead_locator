from django.urls import path
from . import views

app_name = 'locator'

urlpatterns = [
    # Search endpoints
    path('api/v1/locator/search/', views.LocationSearchAPIView.as_view(), name='search'),
    path('api/v1/locator/history/', views.SearchHistoryListAPIView.as_view(), name='history'),
    path('api/v1/locator/history/<uuid:pk>/', views.SearchHistoryDetailAPIView.as_view(), name='history_detail'),
    path('api/v1/locator/history/<uuid:search_id>/export/<str:format>/', views.SearchHistoryExportAPIView.as_view(), name='export'),
    
    # Preferences and settings
    path('api/v1/locator/preferences/', views.UserLocationPreferenceAPIView.as_view(), name='preferences'),
    path('api/v1/locator/excluded/', views.ExcludedLocationListCreateAPIView.as_view(), name='excluded_list'),
    path('api/v1/locator/excluded/<uuid:pk>/', views.ExcludedLocationDetailAPIView.as_view(), name='excluded_detail'),
    path('api/v1/locator/excluded/bulk/', views.bulk_exclude_locations, name='bulk_exclude'),
    
    # Statistics and data
    path('api/v1/locator/stats/', views.LocationStatsAPIView.as_view(), name='stats'),
    path('api/v1/locator/recent/', views.RecentLocationsAPIView.as_view(), name='recent'),
    
    # Health check
    path('api/v1/locator/health/', views.locator_health_check, name='health'),
]