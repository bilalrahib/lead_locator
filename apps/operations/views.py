from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import logging
from datetime import datetime, timedelta

from .models import ManagedLocation, PlacedMachine, VisitLog, CollectionData
from .serializers import (
    ManagedLocationSerializer, ManagedLocationDetailSerializer, ManagedLocationCreateSerializer,
    PlacedMachineSerializer, PlacedMachineDetailSerializer, PlacedMachineCreateSerializer,
    VisitLogSerializer, VisitLogDetailSerializer, VisitLogCreateSerializer,
    CollectionDataSerializer, CollectionDataDetailSerializer, CollectionDataCreateSerializer,
    OperationalReportSerializer, LocationReportSerializer, MachineReportSerializer
)
from .services import LocationService, MachineService, VisitService, CollectionService, ReportService

logger = logging.getLogger(__name__)


# Location Views
class ManagedLocationListAPIView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating managed locations.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ManagedLocationCreateSerializer
        return ManagedLocationSerializer
    
    def get_queryset(self):
        return LocationService.get_user_locations(self.request.user)


class ManagedLocationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, and deleting managed locations.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ManagedLocationDetailSerializer
        return ManagedLocationSerializer
    
    def get_queryset(self):
        return ManagedLocation.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        LocationService.deactivate_location(instance)


# Machine Views
class PlacedMachineListAPIView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating placed machines.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PlacedMachineCreateSerializer
        return PlacedMachineSerializer
    
    def get_queryset(self):
        queryset = MachineService.get_user_machines(self.request.user)
        
        # Filter by location if specified
        location_id = self.request.query_params.get('location')
        if location_id:
            queryset = queryset.filter(managed_location_id=location_id)
        
        # Filter by machine type if specified
        machine_type = self.request.query_params.get('machine_type')
        if machine_type:
            queryset = queryset.filter(machine_type=machine_type)
        
        return queryset


class PlacedMachineDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, and deleting placed machines.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return PlacedMachineDetailSerializer
        return PlacedMachineSerializer
    
    def get_queryset(self):
        return PlacedMachine.objects.filter(managed_location__user=self.request.user)
    
    def perform_destroy(self, instance):
        MachineService.remove_machine(instance)


# Visit Views
class VisitLogListAPIView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating visit logs.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VisitLogCreateSerializer
        return VisitLogSerializer
    
    def get_queryset(self):
        queryset = VisitLog.objects.filter(
            placed_machine__managed_location__user=self.request.user
        ).select_related('placed_machine', 'placed_machine__managed_location')
        
        # Filter by machine if specified
        machine_id = self.request.query_params.get('machine')
        if machine_id:
            queryset = queryset.filter(placed_machine_id=machine_id)
        
        # Filter by visit type if specified
        visit_type = self.request.query_params.get('visit_type')
        if visit_type:
            queryset = queryset.filter(visit_type=visit_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(visit_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(visit_date__lte=end_date)
        
        return queryset.order_by('-visit_date')


class VisitLogDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, and deleting visit logs.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return VisitLogDetailSerializer
        return VisitLogSerializer
    
    def get_queryset(self):
        return VisitLog.objects.filter(
            placed_machine__managed_location__user=self.request.user
        )
    
    def perform_destroy(self, instance):
        VisitService.delete_visit(instance)


# Collection Views
class CollectionDataListAPIView(generics.ListCreateAPIView):
    """
    API endpoint for listing and creating collection data.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CollectionDataCreateSerializer
        return CollectionDataSerializer
    
    def get_queryset(self):
        queryset = CollectionData.objects.filter(
            visit_log__placed_machine__managed_location__user=self.request.user
        ).select_related(
            'visit_log',
            'visit_log__placed_machine',
            'visit_log__placed_machine__managed_location'
        )
        
        # Filter by machine if specified
        machine_id = self.request.query_params.get('machine')
        if machine_id:
            queryset = queryset.filter(visit_log__placed_machine_id=machine_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(visit_log__visit_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(visit_log__visit_date__lte=end_date)
        
        return queryset.order_by('-created_at')


class CollectionDataDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for retrieving, updating, and deleting collection data.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CollectionDataDetailSerializer
        return CollectionDataSerializer
    
    def get_queryset(self):
        return CollectionData.objects.filter(
            visit_log__placed_machine__managed_location__user=self.request.user
        )


# Report Views
class OperationalReportsAPIView(APIView):
    """
    API endpoint for generating operational reports.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Generate operational reports."""
        # Parse date parameters
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        custom_start = request.query_params.get('start_date')
        custom_end = request.query_params.get('end_date')
        
        if custom_start:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d')
            start_date = timezone.make_aware(start_date)
        
        if custom_end:
            end_date = datetime.strptime(custom_end, '%Y-%m-%d')
            end_date = timezone.make_aware(end_date)
        
        # Generate reports
        operational_report = ReportService.generate_operational_report(
            request.user, start_date, end_date
        )
        
        location_reports = ReportService.generate_location_reports(
            request.user, start_date, end_date
        )
        
        machine_reports = ReportService.generate_machine_reports(
            request.user, start_date, end_date
        )
        
        return Response({
            'operational_summary': OperationalReportSerializer(operational_report).data,
            'location_reports': LocationReportSerializer(location_reports, many=True).data,
            'machine_reports': MachineReportSerializer(machine_reports, many=True).data
        })


class ExportReportsAPIView(APIView):
    """
    API endpoint for exporting reports in various formats.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, report_type, format):
        """Export reports in specified format."""
        # Parse date parameters
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        custom_start = request.query_params.get('start_date')
        custom_end = request.query_params.get('end_date')
        
        if custom_start:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d')
            start_date = timezone.make_aware(start_date)
        
        if custom_end:
            end_date = datetime.strptime(custom_end, '%Y-%m-%d')
            end_date = timezone.make_aware(end_date)
        
        # Generate report data
        if report_type == 'operational':
            data = [ReportService.generate_operational_report(request.user, start_date, end_date)]
        elif report_type == 'locations':
            data = ReportService.generate_location_reports(request.user, start_date, end_date)
        elif report_type == 'machines':
            data = ReportService.generate_machine_reports(request.user, start_date, end_date)
        else:
            return Response({'error': 'Invalid report type'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Export in requested format
        if format == 'csv':
            csv_data = ReportService.export_to_csv(data, f'{report_type}_report')
            response = HttpResponse(csv_data.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
            return response
        else:
            return Response({'error': 'Unsupported format'}, status=status.HTTP_400_BAD_REQUEST)


class DashboardSummaryAPIView(APIView):
    """
    API endpoint for dashboard summary data.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get dashboard summary."""
        days = int(request.query_params.get('days', 30))
        
        # Get various summaries
        location_summary = LocationService.get_location_summary(request.user)
        visit_summary = VisitService.get_visit_summary(request.user, days)
        financial_summary = CollectionService.calculate_financial_summary(request.user, days)
        report_summary = ReportService.get_report_summary(request.user, days)
        
        return Response({
            'location_summary': location_summary,
            'visit_summary': visit_summary,
            'financial_summary': financial_summary,
            'report_summary': report_summary
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def operations_health_check(request):
    """Health check endpoint for operations app."""
    try:
        # Test database connections
        locations_count = ManagedLocation.objects.count()
        machines_count = PlacedMachine.objects.count()
        visits_count = VisitLog.objects.count()
        collections_count = CollectionData.objects.count()
        
        return Response({
            'status': 'healthy',
            'locations_count': locations_count,
            'machines_count': machines_count,
            'visits_count': visits_count,
            'collections_count': collections_count,
            'app': 'operations'
        })
        
    except Exception as e:
        logger.error(f"Operations health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'app': 'operations'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)