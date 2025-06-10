from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.accounts.models import UserActivity
from .models import SearchHistory, LocationData, UserLocationPreference, ExcludedLocation
from .serializers import (
    LocationSearchSerializer, SearchHistorySerializer, SearchHistoryDetailSerializer,
    LocationDataSerializer, UserLocationPreferenceSerializer, ExcludedLocationSerializer,
    LocationStatsSerializer, ExportRequestSerializer
)
from .services.location_finder_service import LocationFinderService
from .services.export_service import ExportService
import logging

logger = logging.getLogger(__name__)


class LocationSearchAPIView(APIView):
    """
    API endpoint for searching vending machine locations.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Perform location search."""
        serializer = LocationSearchSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check and update subscription usage
            user = request.user
            if hasattr(user, 'subscription') and user.subscription and user.subscription.is_active:
                subscription = user.subscription
                if not subscription.use_search():
                    return Response({
                        'error': 'Search limit reached for current billing period'
                    }, status=status.HTTP_403_FORBIDDEN)

            # Perform the search
            location_service = LocationFinderService()
            search_history = location_service.find_nearby_places(
                user=user,
                zip_code=serializer.validated_data['zip_code'],
                radius=serializer.validated_data['radius'],
                machine_type=serializer.validated_data['machine_type'],
                building_types_filter=serializer.validated_data.get('building_types_filter'),
                max_results=serializer.validated_data.get('max_results', 20)
            )

            # Log user activity
            UserActivity.log_activity(
                user=user,
                activity_type='search_performed',
                description=f'Location search: {search_history.search_summary}',
                request=request,
                metadata={
                    'search_id': str(search_history.id),
                    'results_count': search_history.results_count,
                    'zip_code': search_history.zip_code,
                    'machine_type': search_history.machine_type
                }
            )

            # Return search results
            serializer = SearchHistoryDetailSerializer(search_history)
            return Response({
                'search_history': serializer.data,
                'message': f'Found {search_history.results_count} potential locations'
            }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in location search for {user.email}: {e}")
            return Response({
                'error': 'An error occurred while searching for locations'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SearchHistoryListAPIView(generics.ListAPIView):
    """
    API endpoint for listing user's search history.
    """
    serializer_class = SearchHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class SearchHistoryDetailAPIView(generics.RetrieveAPIView):
    """
    API endpoint for retrieving specific search history with locations.
    """
    serializer_class = SearchHistoryDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user)


class SearchHistoryExportAPIView(APIView):
    """
    API endpoint for exporting search results.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, search_id, format):
        """Export search results in specified format."""
        # Get search history
        search_history = get_object_or_404(
            SearchHistory,
            id=search_id,
            user=request.user
        )

        if search_history.results_count == 0:
            return Response({
                'error': 'No results to export'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            export_service = ExportService()
            
            if format == 'csv':
                response = export_service.export_to_csv(search_history)
            elif format == 'xlsx':
                response = export_service.export_to_xlsx(search_history)
            elif format == 'docx':
                response = export_service.export_to_docx(search_history)
            else:
                return Response({
                    'error': 'Invalid export format. Use csv, xlsx, or docx.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Log export activity
            UserActivity.log_activity(
                user=request.user,
                activity_type='search_performed',
                description=f'Exported search results: {format.upper()}',
                request=request,
                metadata={
                    'search_id': str(search_history.id),
                    'export_format': format,
                    'results_count': search_history.results_count
                }
            )

            return response

        except Exception as e:
            logger.error(f"Error exporting search results: {e}")
            return Response({
                'error': 'Failed to export search results'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLocationPreferenceAPIView(APIView):
    """
    API endpoint for managing user location preferences.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user location preferences."""
        try:
            preferences = UserLocationPreference.objects.get(user=request.user)
            serializer = UserLocationPreferenceSerializer(preferences)
            return Response(serializer.data)
        except UserLocationPreference.DoesNotExist:
            return Response({
                'message': 'No preferences set',
                'preferences': None
            })

    def post(self, request):
        """Create or update user location preferences."""
        try:
            preferences, created = UserLocationPreference.objects.get_or_create(
                user=request.user
            )
            
            serializer = UserLocationPreferenceSerializer(
                preferences,
                data=request.data,
                partial=True
            )
            
            if serializer.is_valid():
                serializer.save()
                action = 'created' if created else 'updated'
                return Response({
                    'preferences': serializer.data,
                    'message': f'Preferences {action} successfully'
                })
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error managing user preferences: {e}")
            return Response({
                'error': 'Failed to save preferences'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExcludedLocationListCreateAPIView(generics.ListCreateAPIView):
    """
    API endpoint for managing excluded locations.
    """
    serializer_class = ExcludedLocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExcludedLocation.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ExcludedLocationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for managing individual excluded locations.
    """
    serializer_class = ExcludedLocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExcludedLocation.objects.filter(user=self.request.user)


class LocationStatsAPIView(APIView):
    """
    API endpoint for location search statistics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's location search statistics."""
        user = request.user
        
        # Get date range for current month
        current_month_start = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        
        # Total statistics
        total_searches = SearchHistory.objects.filter(user=user).count()
        total_locations = LocationData.objects.filter(
            search_history__user=user
        ).count()
        
        # This month statistics
        searches_this_month = SearchHistory.objects.filter(
            user=user,
            created_at__gte=current_month_start
        ).count()
        
        locations_this_month = LocationData.objects.filter(
            search_history__user=user,
            search_history__created_at__gte=current_month_start
        ).count()
        
        # Favorite machine type
        favorite_machine_type = SearchHistory.objects.filter(
            user=user
        ).values('machine_type').annotate(
            count=Count('machine_type')
        ).order_by('-count').first()
        
        favorite_machine_type_name = 'None'
        if favorite_machine_type:
            machine_type_dict = dict(SearchHistory.MACHINE_TYPE_CHOICES)
            favorite_machine_type_name = machine_type_dict.get(
                favorite_machine_type['machine_type'], 'Unknown'
            )
        
        # Average results per search
        avg_results = SearchHistory.objects.filter(
            user=user
        ).aggregate(avg=Avg('results_count'))['avg'] or 0
        
        # Top ZIP codes
        top_zip_codes = list(
            SearchHistory.objects.filter(user=user)
            .values('zip_code')
            .annotate(count=Count('zip_code'))
            .order_by('-count')[:5]
        )
        
        # Excluded locations count
        excluded_count = ExcludedLocation.objects.filter(user=user).count()
        
        stats_data = {
            'total_searches': total_searches,
            'total_locations_found': total_locations,
            'searches_this_month': searches_this_month,
            'locations_this_month': locations_this_month,
            'favorite_machine_type': favorite_machine_type_name,
            'average_results_per_search': round(avg_results, 1),
            'top_zip_codes': top_zip_codes,
            'excluded_locations_count': excluded_count,
        }
        
        serializer = LocationStatsSerializer(stats_data)
        return Response(serializer.data)


class RecentLocationsAPIView(generics.ListAPIView):
    """
    API endpoint for getting recently found locations.
    """
    serializer_class = LocationDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Get locations from user's recent searches (last 30 days)
        cutoff_date = timezone.now() - timedelta(days=30)
        
        return LocationData.objects.filter(
            search_history__user=self.request.user,
            search_history__created_at__gte=cutoff_date
        ).order_by('-priority_score', '-created_at')[:50]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def locator_health_check(request):
    """Health check for locator app."""
    try:
        # Test database connections
        search_count = SearchHistory.objects.count()
        location_count = LocationData.objects.count()
        
        return Response({
            'status': 'healthy',
            'total_searches': search_count,
            'total_locations': location_count,
            'app': 'locator'
        })
        
    except Exception as e:
        logger.error(f"Locator health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'app': 'locator'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_exclude_locations(request):
    """Bulk exclude multiple locations."""
    try:
        location_ids = request.data.get('location_ids', [])
        reason = request.data.get('reason', 'other')
        notes = request.data.get('notes', '')
        
        if not location_ids:
            return Response({
                'error': 'No location IDs provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get locations and create exclusions
        locations = LocationData.objects.filter(
            id__in=location_ids,
            search_history__user=request.user
        )
        
        exclusions_created = 0
        for location in locations:
            exclusion, created = ExcludedLocation.objects.get_or_create(
                user=request.user,
                google_place_id=location.google_place_id,
                defaults={
                    'location_name': location.name,
                    'reason': reason,
                    'notes': notes
                }
            )
            if created:
                exclusions_created += 1
        
        return Response({
            'message': f'{exclusions_created} locations excluded',
            'total_processed': len(location_ids)
        })
        
    except Exception as e:
        logger.error(f"Error in bulk exclude locations: {e}")
        return Response({
            'error': 'Failed to exclude locations'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)