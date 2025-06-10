from django.urls import path
from . import views

app_name = 'operations'

urlpatterns = [
    # Managed Locations
    path('api/v1/operations/managed-locations/', views.ManagedLocationListAPIView.as_view(), name='managed_locations'),
    path('api/v1/operations/managed-locations/<uuid:pk>/', views.ManagedLocationDetailAPIView.as_view(), name='managed_location_detail'),
    
    # Placed Machines
    path('api/v1/operations/placed-machines/', views.PlacedMachineListAPIView.as_view(), name='placed_machines'),
    path('api/v1/operations/placed-machines/<uuid:pk>/', views.PlacedMachineDetailAPIView.as_view(), name='placed_machine_detail'),
    
    # Visit Logs
    path('api/v1/operations/visit-logs/', views.VisitLogListAPIView.as_view(), name='visit_logs'),
    path('api/v1/operations/visit-logs/<uuid:pk>/', views.VisitLogDetailAPIView.as_view(), name='visit_log_detail'),
    
    # Collection Data
    path('api/v1/operations/collection-data/', views.CollectionDataListAPIView.as_view(), name='collection_data'),
    path('api/v1/operations/collection-data/<uuid:pk>/', views.CollectionDataDetailAPIView.as_view(), name='collection_data_detail'),
    
    # Reports
    path('api/v1/operations/reports/', views.OperationalReportsAPIView.as_view(), name='reports'),
    path('api/v1/operations/reports/export/<str:report_type>/<str:format>/', views.ExportReportsAPIView.as_view(), name='export_reports'),
    path('api/v1/operations/dashboard/', views.DashboardSummaryAPIView.as_view(), name='dashboard'),
    
    # Health Check
    path('api/v1/operations/health/', views.operations_health_check, name='health'),
]