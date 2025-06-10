from django.urls import path
from . import views

app_name = 'pro_locator'

urlpatterns = [
    # Client Management
    path('api/v1/pro/clients/', views.ClientListCreateAPIView.as_view(), name='client_list'),
    path('api/v1/pro/clients/<uuid:pk>/', views.ClientDetailAPIView.as_view(), name='client_detail'),
    path('api/v1/pro/clients/<uuid:client_id>/stats/', views.ClientStatsAPIView.as_view(), name='client_stats'),
    
    # Client Searches
    path('api/v1/pro/search/', views.ClientSearchAPIView.as_view(), name='client_search'),
    path('api/v1/pro/clients/<uuid:client_id>/searches/', views.ClientSearchListAPIView.as_view(), name='client_searches'),
    
    # Client Locations
    path('api/v1/pro/clients/<uuid:client_id>/locations/', views.ClientLocationListAPIView.as_view(), name='client_locations'),
    path('api/v1/pro/locations/<uuid:pk>/', views.ClientLocationUpdateAPIView.as_view(), name='location_update'),
    path('api/v1/pro/clients/<uuid:client_id>/locations/bulk-update/', views.ClientLocationBulkUpdateAPIView.as_view(), name='location_bulk_update'),
    
    # Exports
    path('api/v1/pro/clients/<uuid:client_id>/export/<str:format>/', views.ClientExportAPIView.as_view(), name='client_export'),
    
    # White Label Settings
    path('api/v1/pro/whitelabel-settings/', views.WhiteLabelSettingsAPIView.as_view(), name='whitelabel_settings'),
    
    # Health Check
    path('api/v1/pro/health/', views.pro_locator_health_check, name='health'),
]