from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import logging
from typing import Dict, List, Optional

from ..models import VisitLog, CollectionData

User = get_user_model()
logger = logging.getLogger(__name__)


class CollectionService:
    """Service for managing collection data."""

    @staticmethod
    def create_collection(visit: VisitLog, collection_data: Dict) -> CollectionData:
        """
        Create collection data for a visit.
        
        Args:
            visit: VisitLog instance
            collection_data: Dictionary containing collection information
            
        Returns:
            Created CollectionData instance
        """
        try:
            with transaction.atomic():
                collection = CollectionData.objects.create(
                    visit_log=visit,
                    **collection_data
                )
                
                logger.info(f"Created collection data for visit {visit.id}: ${collection.cash_collected}")
                return collection
                
        except Exception as e:
            logger.error(f"Failed to create collection for visit {visit.id}: {e}")
            raise ValidationError(f"Failed to create collection: {str(e)}")

    @staticmethod
    def update_collection(collection: CollectionData, update_data: Dict) -> CollectionData:
        """
        Update collection data.
        
        Args:
            collection: CollectionData instance
            update_data: Dictionary containing update data
            
        Returns:
            Updated CollectionData instance
        """
        try:
            with transaction.atomic():
                for field, value in update_data.items():
                    if hasattr(collection, field):
                        setattr(collection, field, value)
                
                collection.save()
                
                logger.info(f"Updated collection {collection.id}")
                return collection
                
        except Exception as e:
            logger.error(f"Failed to update collection {collection.id}: {e}")
            raise ValidationError(f"Failed to update collection: {str(e)}")

    @staticmethod
    def get_user_collections(user: User, days: int = 30) -> List[CollectionData]:
        """
        Get recent collections for a user.
        
        Args:
            user: User instance
            days: Number of days to look back
            
        Returns:
            List of CollectionData instances
        """
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        collections = CollectionData.objects.filter(
            visit_log__placed_machine__managed_location__user=user,
            visit_log__visit_date__gte=start_date
        ).select_related(
            'visit_log',
            'visit_log__placed_machine',
            'visit_log__placed_machine__managed_location'
        ).order_by('-created_at')
        
        return list(collections)

    @staticmethod
    def calculate_financial_summary(user: User, days: int = 30) -> Dict:
        """
        Calculate financial summary for a user.
        
        Args:
            user: User instance
            days: Number of days to analyze
            
        Returns:
            Dictionary with financial statistics
        """
        from django.db.models import Sum, Count, Avg
        
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        collections = CollectionData.objects.filter(
            visit_log__placed_machine__managed_location__user=user,
            visit_log__visit_date__gte=start_date
        )
        
        summary = collections.aggregate(
            total_collected=Sum('cash_collected'),
            total_commission=Sum('commission_paid_to_location'),
            total_restock_cost=Sum('restock_cost'),
            total_maintenance_cost=Sum('maintenance_cost'),
            collection_count=Count('id'),
            avg_collection=Avg('cash_collected')
        )
        
        total_collected = summary['total_collected'] or Decimal('0.00')
        total_commission = summary['total_commission'] or Decimal('0.00')
        total_restock = summary['total_restock_cost'] or Decimal('0.00')
        total_maintenance = summary['total_maintenance_cost'] or Decimal('0.00')
        
        total_expenses = total_commission + total_restock + total_maintenance
        net_profit = total_collected - total_expenses
        profit_margin = (net_profit / total_collected * 100) if total_collected > 0 else Decimal('0.00')
        
        return {
            'period_days': days,
            'total_collected': total_collected,
            'total_commission_paid': total_commission,
            'total_restock_cost': total_restock,
            'total_maintenance_cost': total_maintenance,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin': profit_margin,
            'total_collections': summary['collection_count'] or 0,
            'average_per_collection': summary['avg_collection'] or Decimal('0.00'),
            'daily_average': total_collected / days if days > 0 else Decimal('0.00')
        }

    @staticmethod
    def get_top_performing_items(user: User, days: int = 30, limit: int = 10) -> List[Dict]:
        """
        Get top performing machines by revenue.
        
        Args:
            user: User instance
            days: Number of days to analyze
            limit: Number of top items to return
            
        Returns:
            List of dictionaries with machine performance data
        """
        from django.db.models import Sum
        
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        machine_performance = CollectionData.objects.filter(
            visit_log__placed_machine__managed_location__user=user,
            visit_log__visit_date__gte=start_date
        ).values(
            'visit_log__placed_machine__id',
            'visit_log__placed_machine__machine_type',
            'visit_log__placed_machine__machine_identifier',
            'visit_log__placed_machine__managed_location__location_name'
        ).annotate(
            total_revenue=Sum('cash_collected'),
            total_profit=Sum('cash_collected') - Sum('commission_paid_to_location') - Sum('restock_cost') - Sum('maintenance_cost')
        ).order_by('-total_revenue')[:limit]
        
        return list(machine_performance)

    @staticmethod
    def validate_collection_data(collection_data: Dict) -> bool:
        """
        Validate collection data before creation/update.
        
        Args:
            collection_data: Dictionary containing collection information
            
        Returns:
            True if data is valid
        """
        cash_collected = collection_data.get('cash_collected', Decimal('0.00'))
        commission = collection_data.get('commission_paid_to_location', Decimal('0.00'))
        restock_cost = collection_data.get('restock_cost', Decimal('0.00'))
        maintenance_cost = collection_data.get('maintenance_cost', Decimal('0.00'))
        
        if cash_collected < 0:
            raise ValidationError("Cash collected cannot be negative")
        
        if commission < 0:
            raise ValidationError("Commission cannot be negative")
        
        if commission > cash_collected:
            raise ValidationError("Commission cannot exceed cash collected")
        
        if restock_cost < 0:
            raise ValidationError("Restock cost cannot be negative")
        
        if maintenance_cost < 0:
            raise ValidationError("Maintenance cost cannot be negative")
        
        return True