from rest_framework import serializers
from decimal import Decimal


class OperationalReportSerializer(serializers.Serializer):
    """Serializer for operational reports."""
    
    report_period = serializers.CharField()
    total_locations = serializers.IntegerField()
    total_machines = serializers.IntegerField()
    total_collections = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_commission_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_per_machine = serializers.DecimalField(max_digits=10, decimal_places=2)
    most_profitable_location = serializers.CharField()
    top_performing_machine_type = serializers.CharField()


class LocationReportSerializer(serializers.Serializer):
    """Serializer for location-specific reports."""
    
    location_id = serializers.UUIDField()
    location_name = serializers.CharField()
    total_machines = serializers.IntegerField()
    total_collections = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_commission_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    best_performing_machine = serializers.CharField()
    last_visit_date = serializers.DateTimeField()


class MachineReportSerializer(serializers.Serializer):
    """Serializer for machine-specific reports."""
    
    machine_id = serializers.UUIDField()
    machine_type = serializers.CharField()
    machine_identifier = serializers.CharField()
    location_name = serializers.CharField()
    total_collections = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_visits = serializers.IntegerField()
    average_per_visit = serializers.DecimalField(max_digits=8, decimal_places=2)
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_commission_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
    days_since_placement = serializers.IntegerField()
    last_collection_date = serializers.DateTimeField()