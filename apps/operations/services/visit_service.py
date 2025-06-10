from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import logging
from typing import Dict, List, Optional

from ..models import PlacedMachine, VisitLog

User = get_user_model()
logger = logging.getLogger(__name__)


class VisitService:
    """Service for managing machine visits."""

    @staticmethod
    def create_visit(machine: PlacedMachine, visit_data: Dict) -> VisitLog:
        """
        Create a new visit log for a machine.
        
        Args:
            machine: PlacedMachine instance
            visit_data: Dictionary containing visit information
            
        Returns:
            Created VisitLog instance
        """
        try:
            with transaction.atomic():
                visit = VisitLog.objects.create(
                    placed_machine=machine,
                    **visit_data
                )
                
                logger.info(f"Created visit log for {machine} on {visit.visit_date}")
                return visit
                
        except Exception as e:
            logger.error(f"Failed to create visit for machine {machine.id}: {e}")
            raise ValidationError(f"Failed to create visit: {str(e)}")

    @staticmethod
    def get_machine_visits(machine: PlacedMachine, limit: Optional[int] = None) -> List[VisitLog]:
        """
        Get all visits for a machine.
        
        Args:
            machine: PlacedMachine instance
            limit: Maximum number of visits to return
            
        Returns:
            List of VisitLog instances
        """
        queryset = machine.visit_logs.all().order_by('-visit_date')
        
        if limit:
            queryset = queryset[:limit]
        
        return list(queryset)

    @staticmethod
    def get_user_recent_visits(user: User, days: int = 30, limit: int = 50) -> List[VisitLog]:
        """
        Get recent visits for a user's machines.
        
        Args:
            user: User instance
            days: Number of days to look back
            limit: Maximum number of visits to return
            
        Returns:
            List of VisitLog instances
        """
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        visits = VisitLog.objects.filter(
            placed_machine__managed_location__user=user,
            visit_date__gte=start_date
        ).select_related(
            'placed_machine',
            'placed_machine__managed_location'
        ).order_by('-visit_date')[:limit]
        
        return list(visits)

    @staticmethod
    def update_visit(visit: VisitLog, update_data: Dict) -> VisitLog:
        """
        Update a visit log.
        
        Args:
            visit: VisitLog instance
            update_data: Dictionary containing update data
            
        Returns:
            Updated VisitLog instance
        """
        try:
            with transaction.atomic():
                for field, value in update_data.items():
                    if hasattr(visit, field):
                        setattr(visit, field, value)
                
                visit.save()
                
                logger.info(f"Updated visit {visit.id}")
                return visit
                
        except Exception as e:
            logger.error(f"Failed to update visit {visit.id}: {e}")
            raise ValidationError(f"Failed to update visit: {str(e)}")

    @staticmethod
    def delete_visit(visit: VisitLog) -> bool:
        """
        Delete a visit log and its associated collection data.
        
        Args:
            visit: VisitLog instance
            
        Returns:
            True if successful
        """
        try:
            with transaction.atomic():
                visit_id = visit.id
                visit.delete()
                
                logger.info(f"Deleted visit {visit_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete visit {visit.id}: {e}")
            raise ValidationError(f"Failed to delete visit: {str(e)}")

    @staticmethod
    def get_visit_summary(user: User, days: int = 30) -> Dict:
        """
        Get visit summary for a user.
        
        Args:
            user: User instance
            days: Number of days to analyze
            
        Returns:
            Dictionary with visit statistics
        """
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        visits = VisitLog.objects.filter(
            placed_machine__managed_location__user=user,
            visit_date__gte=start_date
        )
        
        total_visits = visits.count()
        
        # Group by visit type
        visit_types = visits.values_list('visit_type', flat=True)
        type_counts = {}
        for visit_type in visit_types:
            type_counts[visit_type] = type_counts.get(visit_type, 0) + 1
        
        # Calculate average visits per machine
        total_machines = PlacedMachine.objects.filter(
            managed_location__user=user,
            is_active=True
        ).count()
        
        avg_visits_per_machine = total_visits / total_machines if total_machines > 0 else 0
        
        return {
            'period_days': days,
            'total_visits': total_visits,
            'visit_types': type_counts,
            'average_visits_per_machine': round(avg_visits_per_machine, 2),
            'most_common_visit_type': max(type_counts, key=type_counts.get) if type_counts else None
        }

    @staticmethod
    def validate_visit_data(visit_data: Dict) -> bool:
        """
        Validate visit data before creation/update.
        
        Args:
            visit_data: Dictionary containing visit information
            
        Returns:
            True if data is valid
        """
        visit_date = visit_data.get('visit_date')
        if visit_date and visit_date > timezone.now():
            raise ValidationError("Visit date cannot be in the future")
        
        return True