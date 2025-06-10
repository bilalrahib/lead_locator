from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import logging
from typing import Dict, List, Optional

from ..models import ManagedLocation, PlacedMachine

User = get_user_model()
logger = logging.getLogger(__name__)


class MachineService:
    """Service for managing placed vending machines."""

    @staticmethod
    def place_machine(location: ManagedLocation, machine_data: Dict) -> PlacedMachine:
        """
        Place a new machine at a location.
        
        Args:
            location: ManagedLocation instance
            machine_data: Dictionary containing machine information
            
        Returns:
            Created PlacedMachine instance
        """
        try:
            with transaction.atomic():
                machine = PlacedMachine.objects.create(
                    managed_location=location,
                    **machine_data
                )
                
                logger.info(f"Placed {machine.get_machine_type_display()} at {location.location_name}")
                return machine
                
        except Exception as e:
            logger.error(f"Failed to place machine at location {location.id}: {e}")
            raise ValidationError(f"Failed to place machine: {str(e)}")

    @staticmethod
    def get_user_machines(user: User, active_only: bool = True) -> List[PlacedMachine]:
        """
        Get all machines for a user.
        
        Args:
            user: User instance
            active_only: Whether to return only active machines
            
        Returns:
            List of PlacedMachine instances
        """
        queryset = PlacedMachine.objects.filter(
            managed_location__user=user
        ).select_related('managed_location')
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-date_placed')

    @staticmethod
    def get_machines_by_location(location: ManagedLocation, active_only: bool = True) -> List[PlacedMachine]:
        """
        Get all machines at a specific location.
        
        Args:
            location: ManagedLocation instance
            active_only: Whether to return only active machines
            
        Returns:
            List of PlacedMachine instances
        """
        queryset = location.placed_machines.all()
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-date_placed')

    @staticmethod
    def update_machine(machine: PlacedMachine, update_data: Dict) -> PlacedMachine:
        """
        Update a placed machine.
        
        Args:
            machine: PlacedMachine instance
            update_data: Dictionary containing update data
            
        Returns:
            Updated PlacedMachine instance
        """
        try:
            with transaction.atomic():
                for field, value in update_data.items():
                    if hasattr(machine, field):
                        setattr(machine, field, value)
                
                machine.save()
                
                logger.info(f"Updated machine {machine.id}")
                return machine
                
        except Exception as e:
            logger.error(f"Failed to update machine {machine.id}: {e}")
            raise ValidationError(f"Failed to update machine: {str(e)}")

    @staticmethod
    def remove_machine(machine: PlacedMachine, create_removal_log: bool = True) -> bool:
        """
        Remove a machine from a location.
        
        Args:
            machine: PlacedMachine instance
            create_removal_log: Whether to create a removal visit log
            
        Returns:
            True if successful
        """
        try:
            with transaction.atomic():
                if create_removal_log:
                    from .visit_service import VisitService
                    VisitService.create_visit(
                        machine=machine,
                        visit_data={
                            'visit_date': timezone.now(),
                            'visit_type': 'removal',
                            'notes': 'Machine removed'
                        }
                    )
                
                machine.is_active = False
                machine.save()
                
                logger.info(f"Removed machine {machine.id} from {machine.managed_location.location_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove machine {machine.id}: {e}")
            raise ValidationError(f"Failed to remove machine: {str(e)}")

    @staticmethod
    def get_machine_performance(machine: PlacedMachine, days: int = 30) -> Dict:
        """
        Get performance statistics for a machine.
        
        Args:
            machine: PlacedMachine instance
            days: Number of days to analyze
            
        Returns:
            Dictionary with performance statistics
        """
        from django.db.models import Sum, Count, Avg
        from ..models import CollectionData
        
        # Calculate date range
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        # Get collection data for the period
        collections = CollectionData.objects.filter(
            visit_log__placed_machine=machine,
            visit_log__visit_date__gte=start_date
        )
        
        stats = collections.aggregate(
            total_collected=Sum('cash_collected'),
            total_commission=Sum('commission_paid_to_location'),
            total_costs=Sum('restock_cost') + Sum('maintenance_cost'),
            visit_count=Count('id'),
            avg_collection=Avg('cash_collected')
        )
        
        total_collected = stats['total_collected'] or Decimal('0.00')
        total_commission = stats['total_commission'] or Decimal('0.00')
        total_costs = stats['total_costs'] or Decimal('0.00')
        
        net_profit = total_collected - total_commission - total_costs
        roi = (net_profit / total_collected * 100) if total_collected > 0 else Decimal('0.00')
        
        return {
            'period_days': days,
            'total_collected': total_collected,
            'total_commission_paid': total_commission,
            'total_costs': total_costs,
            'net_profit': net_profit,
            'roi_percentage': roi,
            'total_visits': stats['visit_count'] or 0,
            'average_per_visit': stats['avg_collection'] or Decimal('0.00'),
            'collections_per_day': total_collected / days if days > 0 else Decimal('0.00')
        }

    @staticmethod
    def validate_machine_data(machine_data: Dict) -> bool:
        """
        Validate machine data before creation/update.
        
        Args:
            machine_data: Dictionary containing machine information
            
        Returns:
            True if data is valid
        """
        commission_rate = machine_data.get('commission_percentage_to_location')
        if commission_rate and (commission_rate < 0 or commission_rate > 100):
            raise ValidationError("Commission percentage must be between 0 and 100")
        
        cost_per_vend = machine_data.get('cost_per_vend')
        if cost_per_vend and cost_per_vend < 0:
            raise ValidationError("Cost per vend cannot be negative")
        
        date_placed = machine_data.get('date_placed')
        if date_placed and date_placed > timezone.now().date():
            raise ValidationError("Date placed cannot be in the future")
        
        return True