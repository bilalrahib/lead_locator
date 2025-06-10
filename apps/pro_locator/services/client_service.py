from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from typing import Dict, List, Optional
import logging

from ..models import ClientProfile, ClientSavedSearch, ClientLocationData

User = get_user_model()
logger = logging.getLogger(__name__)


class ClientService:
    """Service for managing client operations."""

    @staticmethod
    def check_pro_user_permission(user: User) -> bool:
        """Check if user has Elite or Professional subscription."""
        return user.subscription_status in ['ELITE', 'PROFESSIONAL']

    @staticmethod
    def get_user_clients(user: User, include_inactive: bool = False) -> List[ClientProfile]:
        """
        Get all clients for a user.
        
        Args:
            user: User instance
            include_inactive: Whether to include inactive clients
            
        Returns:
            List of ClientProfile instances
        """
        if not ClientService.check_pro_user_permission(user):
            raise PermissionDenied("Client management requires Elite or Professional subscription")

        queryset = ClientProfile.objects.filter(user=user)
        
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-created_at')

    @staticmethod
    @transaction.atomic
    def create_client(user: User, client_data: Dict) -> ClientProfile:
        """
        Create a new client profile.
        
        Args:
            user: User instance
            client_data: Client information dictionary
            
        Returns:
            Created ClientProfile instance
        """
        if not ClientService.check_pro_user_permission(user):
            raise PermissionDenied("Client management requires Elite or Professional subscription")

        # Check client limit based on subscription
        current_clients = ClientProfile.objects.filter(user=user, is_active=True).count()
        max_clients = ClientService._get_max_clients_for_plan(user.subscription_status)
        
        if current_clients >= max_clients:
            raise ValueError(f"Maximum client limit reached ({max_clients} clients)")

        client = ClientProfile.objects.create(user=user, **client_data)
        
        logger.info(f"Created client {client.client_name} for user {user.email}")
        return client

    @staticmethod
    def update_client(user: User, client_id: str, update_data: Dict) -> ClientProfile:
        """
        Update an existing client profile.
        
        Args:
            user: User instance
            client_id: Client UUID
            update_data: Data to update
            
        Returns:
            Updated ClientProfile instance
        """
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        for field, value in update_data.items():
            if hasattr(client, field):
                setattr(client, field, value)
        
        client.save()
        
        logger.info(f"Updated client {client.client_name} for user {user.email}")
        return client

    @staticmethod
    def delete_client(user: User, client_id: str) -> bool:
        """
        Soft delete a client profile.
        
        Args:
            user: User instance
            client_id: Client UUID
            
        Returns:
            Boolean indicating success
        """
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
            client.is_active = False
            client.save()
            
            logger.info(f"Deactivated client {client.client_name} for user {user.email}")
            return True
            
        except ClientProfile.DoesNotExist:
            return False

    @staticmethod
    def get_client_stats(user: User, client_id: str) -> Dict:
        """
        Get comprehensive statistics for a client.
        
        Args:
            user: User instance
            client_id: Client UUID
            
        Returns:
            Dictionary with client statistics
        """
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        from django.db.models import Count, Q
        from django.utils import timezone
        from datetime import timedelta

        # Get date ranges
        thirty_days_ago = timezone.now() - timedelta(days=30)

        # Search statistics
        search_stats = client.saved_searches.aggregate(
            total_searches=Count('id'),
            recent_searches=Count('id', filter=Q(created_at__gte=thirty_days_ago)),
            shared_searches=Count('id', filter=Q(is_shared_with_client=True))
        )

        # Location statistics
        location_stats = client.client_locations.aggregate(
            total_locations=Count('id'),
            new_leads=Count('id', filter=Q(status='new')),
            contacted=Count('id', filter=Q(status='contacted')),
            interested=Count('id', filter=Q(status='interested')),
            placed=Count('id', filter=Q(status='placed')),
            recent_locations=Count('id', filter=Q(created_at__gte=thirty_days_ago))
        )

        return {
            'client_info': {
                'name': client.client_name,
                'contact': client.client_contact_name,
                'location': f"{client.client_city}, {client.client_state}",
                'zip_code': client.client_zip_code,
                'created_date': client.created_at
            },
            'search_stats': {
                'total_searches': search_stats['total_searches'] or 0,
                'recent_searches': search_stats['recent_searches'] or 0,
                'shared_searches': search_stats['shared_searches'] or 0
            },
            'location_stats': {
                'total_locations': location_stats['total_locations'] or 0,
                'new_leads': location_stats['new_leads'] or 0,
                'contacted': location_stats['contacted'] or 0,
                'interested': location_stats['interested'] or 0,
                'machines_placed': location_stats['placed'] or 0,
                'recent_locations': location_stats['recent_locations'] or 0
            }
        }

    @staticmethod
    def _get_max_clients_for_plan(subscription_plan: str) -> int:
        """Get maximum number of clients allowed for subscription plan."""
        limits = {
            'ELITE': 10,
            'PROFESSIONAL': 50
        }
        return limits.get(subscription_plan, 0)

    @staticmethod
    def bulk_update_client_locations(user: User, client_id: str, 
                                   location_updates: List[Dict]) -> Dict:
        """
        Bulk update multiple client locations.
        
        Args:
            user: User instance
            client_id: Client UUID
            location_updates: List of update dictionaries
            
        Returns:
            Update results
        """
        try:
            client = ClientProfile.objects.get(id=client_id, user=user)
        except ClientProfile.DoesNotExist:
            raise ValueError("Client not found or not accessible")

        updated_count = 0
        errors = []

        for update in location_updates:
            try:
                location_id = update.pop('id')
                client_location = ClientLocationData.objects.get(
                    id=location_id,
                    client_profile=client
                )
                
                for field, value in update.items():
                    if hasattr(client_location, field):
                        setattr(client_location, field, value)
                
                client_location.save()
                updated_count += 1
                
            except (KeyError, ClientLocationData.DoesNotExist, ValueError) as e:
                errors.append(f"Error updating location: {str(e)}")

        return {
            'updated_count': updated_count,
            'total_count': len(location_updates),
            'errors': errors
        }