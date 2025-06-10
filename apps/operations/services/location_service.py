from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import logging
from typing import Dict, List, Optional

from ..models import ManagedLocation

User = get_user_model()
logger = logging.getLogger(__name__)


class LocationService:
    """Service for managing vending machine locations."""

    @staticmethod
    def create_location(user: User, location_data: Dict) -> ManagedLocation:
        """
        Create a new managed location for a user.
        
        Args:
            user: User instance
            location_data: Dictionary containing location information
            
        Returns:
            Created ManagedLocation instance
        """
        try:
            with transaction.atomic():
                location = ManagedLocation.objects.create(
                    user=user,
                    **location_data
                )
                
                logger.info(f"Created location {location.location_name} for user {user.email}")
                return location
                
        except Exception as e:
            logger.error(f"Failed to create location for user {user.email}: {e}")
            raise ValidationError(f"Failed to create location: {str(e)}")

    @staticmethod
    def get_user_locations(user: User, active_only: bool = True) -> List[ManagedLocation]:
        """
        Get all locations for a user.
        
        Args:
            user: User instance
            active_only: Whether to return only active locations
            
        Returns:
            List of ManagedLocation instances
        """
        queryset = ManagedLocation.objects.filter(user=user)
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        return queryset.select_related().prefetch_related(
            'placed_machines'
        ).order_by('-created_at')

    @staticmethod
    def update_location(location: ManagedLocation, update_data: Dict) -> ManagedLocation:
        """
        Update a managed location.
        
        Args:
            location: ManagedLocation instance
            update_data: Dictionary containing update data
            
        Returns:
            Updated ManagedLocation instance
        """
        try:
            with transaction.atomic():
                for field, value in update_data.items():
                    if hasattr(location, field):
                        setattr(location, field, value)
                
                location.save()
                
                logger.info(f"Updated location {location.location_name}")
                return location
                
        except Exception as e:
            logger.error(f"Failed to update location {location.id}: {e}")
            raise ValidationError(f"Failed to update location: {str(e)}")

    @staticmethod
    def deactivate_location(location: ManagedLocation) -> bool:
        """
        Deactivate a location and all its machines.
        
        Args:
            location: ManagedLocation instance
            
        Returns:
            True if successful
        """
        try:
            with transaction.atomic():
                # Deactivate all machines at this location
                location.placed_machines.update(is_active=False)
                
                # Deactivate the location
                location.is_active = False
                location.save()
                
                logger.info(f"Deactivated location {location.location_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to deactivate location {location.id}: {e}")
            raise ValidationError(f"Failed to deactivate location: {str(e)}")

    @staticmethod
    def get_location_summary(user: User) -> Dict:
        """
        Get summary statistics for user's locations.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with summary statistics
        """
        locations = ManagedLocation.objects.filter(user=user, is_active=True)
        
        total_locations = locations.count()
        total_machines = sum(loc.total_machines for loc in locations)
        total_revenue = sum(loc.total_revenue_this_month for loc in locations)
        
        # Get most profitable location
        most_profitable = max(
            locations, 
            key=lambda x: x.total_revenue_this_month,
            default=None
        ) if locations else None
        
        return {
            'total_locations': total_locations,
            'total_machines': total_machines,
            'total_revenue_this_month': total_revenue,
            'most_profitable_location': most_profitable.location_name if most_profitable else None,
            'average_revenue_per_location': total_revenue / total_locations if total_locations > 0 else Decimal('0.00')
        }

    @staticmethod
    def validate_location_coordinates(latitude: Optional[Decimal], longitude: Optional[Decimal]) -> bool:
        """
        Validate location coordinates.
        
        Args:
            latitude: Latitude value
            longitude: Longitude value
            
        Returns:
            True if coordinates are valid
        """
        if latitude is None or longitude is None:
            return True  # Coordinates are optional
        
        if not (-90 <= latitude <= 90):
            raise ValidationError("Latitude must be between -90 and 90 degrees")
        
        if not (-180 <= longitude <= 180):
            raise ValidationError("Longitude must be between -180 and 180 degrees")
        
        return True