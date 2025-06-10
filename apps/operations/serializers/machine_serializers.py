from rest_framework import serializers
from ..models import PlacedMachine


class PlacedMachineSerializer(serializers.ModelSerializer):
    """Basic serializer for placed machines."""
    
    machine_type_display = serializers.CharField(source='get_machine_type_display', read_only=True)
    total_collections_this_month = serializers.ReadOnlyField()
    average_per_visit = serializers.ReadOnlyField()
    days_since_placement = serializers.ReadOnlyField()
    location_name = serializers.CharField(source='managed_location.location_name', read_only=True)

    class Meta:
        model = PlacedMachine
        fields = [
            'id', 'managed_location', 'location_name', 'machine_type', 
            'machine_type_display', 'machine_identifier', 'date_placed',
            'commission_percentage_to_location', 'vend_price_range', 
            'cost_per_vend', 'image', 'is_active', 'notes',
            'total_collections_this_month', 'average_per_visit',
            'days_since_placement', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlacedMachineDetailSerializer(PlacedMachineSerializer):
    """Detailed serializer for placed machines with visit history."""
    
    recent_visits = serializers.SerializerMethodField()
    performance_stats = serializers.SerializerMethodField()
    
    class Meta(PlacedMachineSerializer.Meta):
        fields = PlacedMachineSerializer.Meta.fields + [
            'recent_visits', 'performance_stats'
        ]
    
    def get_recent_visits(self, obj):
        """Get recent visits for this machine."""
        from .visit_serializers import VisitLogSerializer
        visits = obj.visit_logs.order_by('-visit_date')[:10]
        return VisitLogSerializer(visits, many=True).data
    
    def get_performance_stats(self, obj):
        """Get performance statistics."""
        from django.db.models import Sum, Count, Avg
        from ..models import CollectionData
        
        stats = CollectionData.objects.filter(
            visit_log__placed_machine=obj
        ).aggregate(
            total_collected=Sum('cash_collected'),
            total_commission=Sum('commission_paid_to_location'),
            total_visits=Count('id'),
            avg_collection=Avg('cash_collected')
        )
        
        return {
            'total_collected': stats['total_collected'] or 0,
            'total_commission_paid': stats['total_commission'] or 0,
            'total_visits': stats['total_visits'] or 0,
            'average_per_collection': stats['avg_collection'] or 0,
            'net_profit': (stats['total_collected'] or 0) - (stats['total_commission'] or 0)
        }


class PlacedMachineCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating placed machines."""
    
    class Meta:
        model = PlacedMachine
        fields = [
            'managed_location', 'machine_type', 'machine_identifier',
            'date_placed', 'commission_percentage_to_location',
            'vend_price_range', 'cost_per_vend', 'image', 'notes'
        ]
    
    def validate_managed_location(self, value):
        """Ensure user owns the location."""
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("You can only add machines to your own locations.")
        return value