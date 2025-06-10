from rest_framework import serializers
from decimal import Decimal
from ..models import CollectionData


class CollectionDataSerializer(serializers.ModelSerializer):
    """Basic serializer for collection data."""
    
    net_profit = serializers.ReadOnlyField()
    profit_margin = serializers.ReadOnlyField()
    visit_info = serializers.SerializerMethodField()

    class Meta:
        model = CollectionData
        fields = [
            'id', 'visit_log', 'visit_info', 'cash_collected', 
            'items_sold_value', 'commission_paid_to_location',
            'restock_cost', 'maintenance_cost', 'restock_notes',
            'net_profit', 'profit_margin', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_visit_info(self, obj):
        """Get basic visit information."""
        return {
            'visit_date': obj.visit_log.visit_date,
            'visit_type': obj.visit_log.get_visit_type_display(),
            'machine_type': obj.visit_log.placed_machine.get_machine_type_display(),
            'location_name': obj.visit_log.placed_machine.managed_location.location_name
        }


class CollectionDataDetailSerializer(CollectionDataSerializer):
    """Detailed serializer for collection data."""
    
    machine_details = serializers.SerializerMethodField()
    
    class Meta(CollectionDataSerializer.Meta):
        fields = CollectionDataSerializer.Meta.fields + ['machine_details']
    
    def get_machine_details(self, obj):
        """Get detailed machine information."""
        machine = obj.visit_log.placed_machine
        return {
            'machine_id': machine.id,
            'machine_type': machine.get_machine_type_display(),
            'machine_identifier': machine.machine_identifier,
            'commission_rate': machine.commission_percentage_to_location,
            'location_name': machine.managed_location.location_name,
            'location_address': machine.managed_location.address_details
        }


class CollectionDataCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating collection data."""
    
    class Meta:
        model = CollectionData
        fields = [
            'visit_log', 'cash_collected', 'items_sold_value',
            'commission_paid_to_location', 'restock_cost', 
            'maintenance_cost', 'restock_notes'
        ]
    
    def validate_visit_log(self, value):
        """Ensure user owns the visit log."""
        user = self.context['request'].user
        if value.placed_machine.managed_location.user != user:
            raise serializers.ValidationError("You can only add collection data to your own visit logs.")
        return value
    
    def validate(self, data):
        """Validate collection data consistency."""
        cash_collected = data.get('cash_collected', Decimal('0.00'))
        commission = data.get('commission_paid_to_location')
        
        if commission and commission > cash_collected:
            raise serializers.ValidationError({
                'commission_paid_to_location': 'Commission cannot exceed cash collected.'
            })
        
        return data