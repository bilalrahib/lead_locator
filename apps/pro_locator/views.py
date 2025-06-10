from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
# from apps.accounts.models import UserActivity
from .models import ClientProfile, ClientSavedSearch, ClientLocationData, WhiteLabelSettings
from .serializers import (
    ClientProfileSerializer, ClientProfileCreateSerializer, ClientProfileDetailSerializer,
    ClientSavedSearchSerializer, ClientLocationDataSerializer, ClientLocationDataUpdateSerializer,
    ClientSearchRequestSerializer, ClientSearchResultSerializer,
    ExportRequestSerializer, WhiteLabelSettingsSerializer, WhiteLabelSettingsUpdateSerializer
)
from .services import ClientService, ClientSearchService, ClientExportService, WhiteLabelService

from django.core.exceptions import PermissionDenied  # Add this import

# Check if UserActivity exists in accounts app
try:
    from apps.accounts.models import UserActivity
except ImportError:
    # Create a dummy UserActivity class if it doesn't exist
    class UserActivity:
        @staticmethod
        def log_activity(user, activity_type, description, request=None, metadata=None):
            pass


import logging

logger = logging.getLogger(__name__)


class ProUserRequiredMixin:
    """Mixin to ensure user has Elite or Professional subscription."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not request.user.subscription_status in ['ELITE', 'PROFESSIONAL']:
            return Response({
                'error': 'Pro features require Elite or Professional subscription'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return super().dispatch(request, *args, **kwargs)


# Client Management Views
class ClientListCreateAPIView(ProUserRequiredMixin, generics.ListCreateAPIView):
    """API endpoint for listing and creating clients."""
    
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ClientProfileCreateSerializer
        return ClientProfileSerializer

    def get_queryset(self):
        return ClientService.get_user_clients(
            self.request.user,
            include_inactive=self.request.query_params.get('include_inactive', False)
        )

    def perform_create(self, serializer):
        client = serializer.save()
        
        # Log activity
        UserActivity.log_activity(
            user=self.request.user,
            activity_type='client_created',
            description=f'Created client: {client.client_name}',
            request=self.request,
            metadata={'client_id': str(client.id)}
        )


class ClientDetailAPIView(ProUserRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """API endpoint for client detail operations."""
    
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ClientProfileDetailSerializer
        return ClientProfileSerializer

    def get_queryset(self):
        return ClientProfile.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        client = serializer.save()
        
        UserActivity.log_activity(
            user=self.request.user,
            activity_type='client_updated',
            description=f'Updated client: {client.client_name}',
            request=self.request,
            metadata={'client_id': str(client.id)}
        )

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()
        
        UserActivity.log_activity(
            user=self.request.user,
            activity_type='client_deleted',
            description=f'Deleted client: {instance.client_name}',
            request=self.request,
            metadata={'client_id': str(instance.id)}
        )


class ClientStatsAPIView(ProUserRequiredMixin, APIView):
    """API endpoint for client statistics."""
    
    permission_classes = [IsAuthenticated]

    def get(self, request, client_id):
        """Get comprehensive client statistics."""
        try:
            stats = ClientService.get_client_stats(request.user, client_id)
            return Response(stats)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)


# Client Search Views
class ClientSearchAPIView(ProUserRequiredMixin, APIView):
    """API endpoint for performing client searches."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Perform a search for a specific client."""
        serializer = ClientSearchRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            search_service = ClientSearchService()
            result = search_service.perform_client_search(
                user=request.user,
                client_id=str(serializer.validated_data['client_id']),
                search_params=serializer.validated_data
            )

            result_serializer = ClientSearchResultSerializer(result)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)

        except (ValueError, PermissionError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in client search: {e}")
            return Response({
                'error': 'An error occurred while performing the search'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientSearchListAPIView(ProUserRequiredMixin, generics.ListAPIView):
    """API endpoint for listing client searches."""
    
    serializer_class = ClientSavedSearchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        client_id = self.kwargs['client_id']
        
        # Verify client ownership
        try:
            client = ClientProfile.objects.get(id=client_id, user=self.request.user)
        except ClientProfile.DoesNotExist:
            return ClientSavedSearch.objects.none()
        
        return client.saved_searches.order_by('-created_at')


class ClientLocationListAPIView(ProUserRequiredMixin, generics.ListAPIView):
    """API endpoint for listing client locations."""
    
    serializer_class = ClientLocationDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        client_id = self.kwargs['client_id']
        
        # Verify client ownership
        try:
            client = ClientProfile.objects.get(id=client_id, user=self.request.user)
        except ClientProfile.DoesNotExist:
            return ClientLocationData.objects.none()
        
        queryset = client.client_locations.select_related('location_data', 'saved_search')
        
        # Apply filters
        status_filter = self.request.query_params.getlist('status')
        if status_filter:
            queryset = queryset.filter(status__in=status_filter)
        
        priority_min = self.request.query_params.get('priority_min')
        if priority_min:
            queryset = queryset.filter(priority__gte=int(priority_min))
        
        return queryset.order_by('-priority', '-created_at')


class ClientLocationUpdateAPIView(ProUserRequiredMixin, generics.UpdateAPIView):
    """API endpoint for updating client location data."""
    
    serializer_class = ClientLocationDataUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClientLocationData.objects.filter(client_profile__user=self.request.user)

    def perform_update(self, serializer):
        location = serializer.save()
        
        UserActivity.log_activity(
            user=self.request.user,
            activity_type='client_location_updated',
            description=f'Updated location status: {location.location_data.name}',
            request=self.request,
            metadata={
                'client_id': str(location.client_profile.id),
                'location_id': str(location.id),
                'status': location.status
            }
        )


# Export Views
class ClientExportAPIView(ProUserRequiredMixin, APIView):
    """API endpoint for exporting client data."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request, client_id, format):
        """Export client locations in specified format."""
        if format not in ['csv', 'pdf']:
            return Response({
                'error': 'Invalid format. Use csv or pdf.'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExportRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            export_service = ClientExportService()
            
            if format == 'csv':
                response = export_service.export_client_locations_csv(
                    user=request.user,
                    client_id=client_id,
                    export_options=serializer.validated_data
                )
            else:  # pdf
                response = export_service.export_client_locations_pdf(
                    user=request.user,
                    client_id=client_id,
                    export_options=serializer.validated_data
                )

            # Log export activity
            UserActivity.log_activity(
                user=request.user,
                activity_type='client_export',
                description=f'Exported client data: {format.upper()}',
                request=request,
                metadata={
                    'client_id': client_id,
                    'export_format': format
                }
            )

            return response

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error exporting client data: {e}")
            return Response({
                'error': 'Failed to export client data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# White Label Views
class WhiteLabelSettingsAPIView(APIView):
    """API endpoint for white label settings."""
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get white label settings."""
        if request.user.subscription_status != 'PROFESSIONAL':
            return Response({
                'error': 'White-label features are only available for Professional plan users'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            settings = WhiteLabelSettings.objects.get(user=request.user)
            serializer = WhiteLabelSettingsSerializer(settings)
            return Response(serializer.data)
        except WhiteLabelSettings.DoesNotExist:
            return Response({
                'message': 'No white-label settings configured',
                'settings': None
            })

    def post(self, request):
        """Create or update white label settings."""
        if request.user.subscription_status != 'PROFESSIONAL':
            return Response({
                'error': 'White-label features are only available for Professional plan users'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            settings = WhiteLabelService.get_or_create_settings(request.user)
            
            serializer = WhiteLabelSettingsUpdateSerializer(
                settings,
                data=request.data,
                context={'request': request},
                partial=True
            )
            
            if serializer.is_valid():
                settings = serializer.save()
                
                UserActivity.log_activity(
                    user=request.user,
                    activity_type='whitelabel_updated',
                    description='Updated white-label settings',
                    request=request
                )
                
                response_serializer = WhiteLabelSettingsSerializer(settings)
                return Response(response_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error managing white-label settings: {e}")
            return Response({
                'error': 'Failed to update white-label settings'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Bulk Operations
class ClientLocationBulkUpdateAPIView(ProUserRequiredMixin, APIView):
    """API endpoint for bulk updating client locations."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request, client_id):
        """Bulk update multiple client locations."""
        try:
            result = ClientService.bulk_update_client_locations(
                user=request.user,
                client_id=client_id,
                location_updates=request.data.get('updates', [])
            )
            
            UserActivity.log_activity(
                user=request.user,
                activity_type='client_bulk_update',
                description=f'Bulk updated {result["updated_count"]} locations',
                request=request,
                metadata={
                    'client_id': client_id,
                    'updated_count': result['updated_count'],
                    'total_count': result['total_count']
                }
            )
            
            return Response(result)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in bulk update: {e}")
            return Response({
                'error': 'Failed to perform bulk update'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Health Check
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def pro_locator_health_check(request):
    """Health check for pro locator app."""
    try:
        # Test database connections
        clients_count = ClientProfile.objects.count()
        searches_count = ClientSavedSearch.objects.count()
        
        return Response({
            'status': 'healthy',
            'total_clients': clients_count,
            'total_searches': searches_count,
            'app': 'pro_locator'
        })
        
    except Exception as e:
        logger.error(f"Pro locator health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'app': 'pro_locator'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)