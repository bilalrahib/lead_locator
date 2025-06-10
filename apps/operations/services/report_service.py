from django.db.models import Sum, Count, Avg, Q, Max
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
import csv
import io
from typing import Dict, List, Optional
import logging

from ..models import ManagedLocation, PlacedMachine, VisitLog, CollectionData

User = get_user_model()
logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating operational reports."""

    @staticmethod
    def generate_operational_report(user: User, start_date: timezone.datetime, end_date: timezone.datetime) -> Dict:
        """
        Generate comprehensive operational report.
        
        Args:
            user: User instance
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Dictionary with report data
        """
        # Basic counts
        total_locations = ManagedLocation.objects.filter(user=user, is_active=True).count()
        total_machines = PlacedMachine.objects.filter(
            managed_location__user=user,
            is_active=True
        ).count()
        
        # Financial data
        collections = CollectionData.objects.filter(
            visit_log__placed_machine__managed_location__user=user,
            visit_log__visit_date__range=[start_date, end_date]
        )
        
        financial_summary = collections.aggregate(
            total_collections=Sum('cash_collected'),
            total_commission=Sum('commission_paid_to_location'),
            total_restock=Sum('restock_cost'),
            total_maintenance=Sum('maintenance_cost')
        )
        
        total_collected = financial_summary['total_collections'] or Decimal('0.00')
        total_commission = financial_summary['total_commission'] or Decimal('0.00')
        total_restock = financial_summary['total_restock'] or Decimal('0.00')
        total_maintenance = financial_summary['total_maintenance'] or Decimal('0.00')
        
        total_expenses = total_commission + total_restock + total_maintenance
        net_profit = total_collected - total_expenses
        profit_margin = (net_profit / total_collected * 100) if total_collected > 0 else Decimal('0.00')
        
        # Performance metrics
        average_per_machine = total_collected / total_machines if total_machines > 0 else Decimal('0.00')
        
        # Most profitable location
        location_profits = collections.values(
            'visit_log__placed_machine__managed_location__location_name'
        ).annotate(
            profit=Sum('cash_collected') - Sum('commission_paid_to_location') - Sum('restock_cost') - Sum('maintenance_cost')
        ).order_by('-profit').first()
        
        most_profitable_location = location_profits['visit_log__placed_machine__managed_location__location_name'] if location_profits else 'N/A'
        
        # Top performing machine type
        machine_type_performance = collections.values(
            'visit_log__placed_machine__machine_type'
        ).annotate(
            total_revenue=Sum('cash_collected')
        ).order_by('-total_revenue').first()
        
        top_machine_type = machine_type_performance['visit_log__placed_machine__machine_type'] if machine_type_performance else 'N/A'
        
        period_days = (end_date - start_date).days + 1
        report_period = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({period_days} days)"
        
        return {
            'report_period': report_period,
            'total_locations': total_locations,
            'total_machines': total_machines,
            'total_collections': total_collected,
            'total_commission_paid': total_commission,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin': profit_margin,
            'average_per_machine': average_per_machine,
            'most_profitable_location': most_profitable_location,
            'top_performing_machine_type': top_machine_type
        }

    @staticmethod
    def generate_location_reports(user: User, start_date: timezone.datetime, end_date: timezone.datetime) -> List[Dict]:
        """
        Generate reports for each location.
        
        Args:
            user: User instance
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            List of location report dictionaries
        """
        locations = ManagedLocation.objects.filter(user=user, is_active=True)
        location_reports = []
        
        for location in locations:
            collections = CollectionData.objects.filter(
                visit_log__placed_machine__managed_location=location,
                visit_log__visit_date__range=[start_date, end_date]
            )
            
            financial_data = collections.aggregate(
                total_collected=Sum('cash_collected'),
                total_commission=Sum('commission_paid_to_location'),
                total_expenses=Sum('restock_cost') + Sum('maintenance_cost')
            )
            
            total_collected = financial_data['total_collected'] or Decimal('0.00')
            total_commission = financial_data['total_commission'] or Decimal('0.00')
            total_expenses = financial_data['total_expenses'] or Decimal('0.00')
            
            net_profit = total_collected - total_commission - total_expenses
            profit_margin = (net_profit / total_collected * 100) if total_collected > 0 else Decimal('0.00')
            
            # Best performing machine at this location
            best_machine = collections.values(
                'visit_log__placed_machine__machine_type',
                'visit_log__placed_machine__machine_identifier'
            ).annotate(
                revenue=Sum('cash_collected')
            ).order_by('-revenue').first()
            
            best_machine_name = f"{best_machine['visit_log__placed_machine__machine_type']} ({best_machine['visit_log__placed_machine__machine_identifier']})" if best_machine else 'N/A'
            
            # Last visit date
            last_visit = VisitLog.objects.filter(
                placed_machine__managed_location=location
            ).order_by('-visit_date').first()
            
            location_reports.append({
                'location_id': location.id,
                'location_name': location.location_name,
                'total_machines': location.total_machines,
                'total_collections': total_collected,
                'total_commission_paid': total_commission,
                'net_profit': net_profit,
                'profit_margin': profit_margin,
                'best_performing_machine': best_machine_name,
                'last_visit_date': last_visit.visit_date if last_visit else None
            })
        
        return location_reports

    @staticmethod
    def generate_machine_reports(user: User, start_date: timezone.datetime, end_date: timezone.datetime) -> List[Dict]:
        """
        Generate reports for each machine.
        
        Args:
            user: User instance
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            List of machine report dictionaries
        """
        machines = PlacedMachine.objects.filter(
            managed_location__user=user,
            is_active=True
        ).select_related('managed_location')
        
        machine_reports = []
        
        for machine in machines:
            collections = CollectionData.objects.filter(
                visit_log__placed_machine=machine,
                visit_log__visit_date__range=[start_date, end_date]
            )
            
            financial_data = collections.aggregate(
                total_collected=Sum('cash_collected'),
                total_commission=Sum('commission_paid_to_location'),
                total_costs=Sum('restock_cost') + Sum('maintenance_cost'),
                visit_count=Count('id')
            )
            
            total_collected = financial_data['total_collected'] or Decimal('0.00')
            total_commission = financial_data['total_commission'] or Decimal('0.00')
            total_costs = financial_data['total_costs'] or Decimal('0.00')
            visit_count = financial_data['visit_count'] or 0
            
            net_profit = total_collected - total_commission - total_costs
            average_per_visit = total_collected / visit_count if visit_count > 0 else Decimal('0.00')
            
            # Last collection date
            last_collection = collections.order_by('-visit_log__visit_date').first()
            
            machine_reports.append({
                'machine_id': machine.id,
                'machine_type': machine.get_machine_type_display(),
                'machine_identifier': machine.machine_identifier or 'N/A',
                'location_name': machine.managed_location.location_name,
                'total_collections': total_collected,
                'total_visits': visit_count,
                'average_per_visit': average_per_visit,
                'commission_rate': machine.commission_percentage_to_location,
                'total_commission_paid': total_commission,
                'net_profit': net_profit,
                'days_since_placement': machine.days_since_placement,
                'last_collection_date': last_collection.visit_log.visit_date if last_collection else None
            })
        
        return machine_reports

    @staticmethod
    def export_to_csv(data: List[Dict], filename: str) -> io.StringIO:
        """
        Export report data to CSV format.
        
        Args:
            data: List of dictionaries containing report data
            filename: Name for the CSV file
            
        Returns:
            StringIO object containing CSV data
        """
        if not data:
            return io.StringIO()
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        output.seek(0)
        return output

    @staticmethod
    def get_report_summary(user: User, days: int = 30) -> Dict:
        """
        Get a quick summary for dashboard display.
        
        Args:
            user: User instance
            days: Number of days to analyze
            
        Returns:
            Dictionary with summary statistics
        """
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)
        
        # Quick financial summary
        collections = CollectionData.objects.filter(
            visit_log__placed_machine__managed_location__user=user,
            visit_log__visit_date__range=[start_date, end_date]
        )
        
        summary = collections.aggregate(
            total_revenue=Sum('cash_collected'),
            total_profit=Sum('cash_collected') - Sum('commission_paid_to_location') - Sum('restock_cost') - Sum('maintenance_cost'),
            total_visits=Count('id')
        )
        
        total_revenue = summary['total_revenue'] or Decimal('0.00')
        total_profit = summary['total_profit'] or Decimal('0.00')
        
        # Activity metrics
        total_locations = ManagedLocation.objects.filter(user=user, is_active=True).count()
        total_machines = PlacedMachine.objects.filter(
            managed_location__user=user,
            is_active=True
        ).count()
        
        return {
            'period_days': days,
            'total_locations': total_locations,
            'total_machines': total_machines,
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'total_visits': summary['total_visits'] or 0,
            'average_revenue_per_day': total_revenue / days if days > 0 else Decimal('0.00'),
            'profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0.00')
        }