from rest_framework import serializers
from ..models import ManagedLocation


class ManagedLocationSerializer(serializers.ModelSerializer):
    """Basic serializer for managed locations."""
    
    total_machines = serializers.ReadOnlyField()
    total_revenue_this_month = serializers.ReadOnlyField()
    coordinates = serializers.ReadOnlyField()

    class Meta:
        model = ManagedLocation
        fields = [
            'id', 'location_name', 'address_details', 'contact_person',
            'contact_phone', 'contact_email', 'image', 'notes', 'is_active',
            'latitude', 'longitude', 'coordinates', 'total_machines', 
            'total_revenue_this_month', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ManagedLocationDetailSerializer(ManagedLocationSerializer):
    """Detailed serializer for managed locations with related data."""
    
    placed_machines = serializers.SerializerMethodField()
    recent_visits = serializers.SerializerMethodField()
    
    class Meta(ManagedLocationSerializer.Meta):
        fields = ManagedLocationSerializer.Meta.fields + [
            'placed_machines', 'recent_visits'
        ]
    
    def get_placed_machines(self, obj):
        """Get basic info about placed machines."""
        from .machine_serializers import PlacedMachineSerializer
        machines = obj.placed_machines.filter(is_active=True)
        return PlacedMachineSerializer(machines, many=True).data
    
    def get_recent_visits(self, obj):
        """Get recent visits for this location."""
        from .visit_serializers import VisitLogSerializer
        from ..models import VisitLog
        recent_visits = VisitLog.objects.filter(
            placed_machine__managed_location=obj
        ).order_by('-visit_date')[:5]
        return VisitLogSerializer(recent_visits, many=True).data


class ManagedLocationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating managed locations."""
    
    class Meta:
        model = ManagedLocation
        fields = [
            'location_name', 'address_details', 'contact_person',
            'contact_phone', 'contact_email', 'image', 'notes',
            'latitude', 'longitude'
        ]
    
    def create(self, validated_data):
        """Create location with current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)