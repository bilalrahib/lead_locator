from django.db import transaction
from django.contrib.auth import get_user_model
from typing import Dict, List, Optional
import logging

from apps.locator.services import LocationFinderService
from apps.locator.models import SearchHistory, LocationData
from ..models import ClientProfile, ClientSavedSearch, ClientLocationData
from .client_service import ClientService

User = get_user_model()
logger = logging.getLogger(__name__)


class ClientSearchService:
    """Service for managing client-specific searches."""

    def __init__(self):
        self.location_finder = LocationFinderService()

    @transaction.atomic
    def perform_client_search(self, user: User, client_id: str, search_params: Dict) -> Dict:
        """
        Perform a search specifically for a client.
        
        Args:
            user: User instance
            client_id: Client UUID
            search_params: Search parameters
            
        Returns:
            Search results with client assignment
        """
        # Verify permissions
        if not ClientService.check_pro_user_permission(user):
            raise PermissionDenied("Client searches require Elite or Professional subscription")

        # Get client
        try:
            client = ClientProfile.objects.get(id=client_id, user=user, is_active=True)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        # Check search limits
        self._check_client_search_limits(user)

        # Perform the search
        search_history = self.location_finder.find_nearby_places(
            user=user,
            zip_code=search_params['zip_code'],
            radius=search_params['radius'],
            machine_type=search_params['machine_type'],
            building_types_filter=search_params.get('building_types_filter'),
            max_results=search_params.get('max_results', 20)
        )

        # Create client saved search
        client_saved_search = ClientSavedSearch.objects.create(
            client_profile=client,
            search_history=search_history,
            search_name=search_params['search_name'],
            notes=search_params.get('client_notes', '')
        )

        # Assign locations to client if requested
        locations_assigned = 0
        if search_params.get('assign_to_client', True):
            locations_assigned = self._assign_locations_to_client(
                client_saved_search, search_history.locations.all()
            )

        logger.info(f"Performed client search for {client.client_name}: {search_history.results_count} results")

        return {
            'search_history': search_history,
            'client_saved_search': client_saved_search,
            'locations_assigned': locations_assigned,
            'message': f'Found {search_history.results_count} locations for {client.client_name}'
        }

    def get_client_searches(self, user: User, client_id: str) -> List[ClientSavedSearch]:
        """
        Get all searches for a specific client.
        
        Args:
            user: User instance
            client_id: Client UUID
            
        Returns:
            List of ClientSavedSearch instances
        """
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        return client.saved_searches.order_by('-created_at')

    def get_client_locations(self, user: User, client_id: str, 
                           status_filter: Optional[List[str]] = None) -> List[ClientLocationData]:
        """
        Get all locations assigned to a client.
        
        Args:
            user: User instance
            client_id: Client UUID
            status_filter: Optional status filter
            
        Returns:
            List of ClientLocationData instances
        """
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        queryset = client.client_locations.select_related('location_data', 'saved_search')
        
        if status_filter:
            queryset = queryset.filter(status__in=status_filter)
        
        return queryset.order_by('-priority', '-created_at')

    @transaction.atomic
    def assign_location_to_client(self, user: User, client_id: str, 
                                location_id: str, search_id: str, 
                                assignment_data: Dict) -> ClientLocationData:
        """
        Manually assign a location to a client.
        
        Args:
            user: User instance
            client_id: Client UUID
            location_id: LocationData UUID
            search_id: ClientSavedSearch UUID
            assignment_data: Assignment information
            
        Returns:
            Created ClientLocationData instance
        """
        # Get client
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        # Get location data
        try:
            location_data = LocationData.objects.get(
                id=location_id,
                search_history__user=user
            )
        except LocationData.DoesNotExist:
            raise ValueError("Location not found or not accessible")

        # Get saved search
        try:
            saved_search = ClientSavedSearch.objects.get(
                id=search_id,
                client_profile=client
            )
        except ClientSavedSearch.DoesNotExist:
            raise ValueError("Saved search not found or not accessible")

        # Check if already assigned
        if ClientLocationData.objects.filter(
            client_profile=client,
            location_data=location_data,
            saved_search=saved_search
        ).exists():
            raise ValueError("Location already assigned to this client for this search")

        # Create assignment
        client_location = ClientLocationData.objects.create(
            client_profile=client,
            location_data=location_data,
            saved_search=saved_search,
            notes=assignment_data.get('notes', ''),
            priority=assignment_data.get('priority', 0),
            status=assignment_data.get('status', 'new')
        )

        logger.info(f"Assigned location {location_data.name} to client {client.client_name}")
        return client_location

    def update_location_status(self, user: User, client_location_id: str, 
                             status_data: Dict) -> ClientLocationData:
        """
        Update the status of a client location.
        
        Args:
            user: User instance
            client_location_id: ClientLocationData UUID
            status_data: Status update data
            
        Returns:
            Updated ClientLocationData instance
        """
        try:
            client_location = ClientLocationData.objects.get(
                id=client_location_id,
                client_profile__user=user
            )
        except ClientLocationData.DoesNotExist:
            raise ValueError("Client location not found or not accessible")

        # Update fields
        for field, value in status_data.items():
            if hasattr(client_location, field):
                setattr(client_location, field, value)

        client_location.save()

        logger.info(f"Updated location status for {client_location.location_data.name}")
        return client_location

    def _check_client_search_limits(self, user: User):
        """Check if user can perform client searches."""
        # Check subscription-based limits
        if user.subscription_status == 'ELITE':
            # Elite users get 10 client searches per month
            from django.utils import timezone
            current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            client_searches_this_month = ClientSavedSearch.objects.filter(
                client_profile__user=user,
                created_at__gte=current_month_start
            ).count()
            
            if client_searches_this_month >= 10:
                raise ValueError("Monthly client search limit reached (10 searches)")
                
        elif user.subscription_status == 'PROFESSIONAL':
            # Professional users get unlimited client searches
            pass
        else:
            raise ValueError("Client searches require Elite or Professional subscription")

    def _assign_locations_to_client(self, client_saved_search: ClientSavedSearch, 
                                  locations: List[LocationData]) -> int:
        """Bulk assign locations to a client from a search."""
        assignments = []
        
        for location in locations:
            # Check if already assigned
            if not ClientLocationData.objects.filter(
                client_profile=client_saved_search.client_profile,
                location_data=location,
                saved_search=client_saved_search
            ).exists():
                assignments.append(ClientLocationData(
                    client_profile=client_saved_search.client_profile,
                    location_data=location,
                    saved_search=client_saved_search,
                    priority=location.priority_score,
                    status='new'
                ))

        if assignments:
            ClientLocationData.objects.bulk_create(assignments)
        
        return len(assignments)

    def share_search_with_client(self, user: User, search_id: str) -> ClientSavedSearch:
        """
        Mark a search as shared with the client.
        
        Args:
            user: User instance
            search_id: ClientSavedSearch UUID
            
        Returns:
            Updated ClientSavedSearch instance
        """
        try:
            client_search = ClientSavedSearch.objects.get(
                id=search_id,
                client_profile__user=user
            )
        except ClientSavedSearch.DoesNotExist:
            raise ValueError("Client search not found or not accessible")

        client_search.mark_shared()
        
        logger.info(f"Shared search {client_search.search_name} with client {client_search.client_profile.client_name}")
        return client_search