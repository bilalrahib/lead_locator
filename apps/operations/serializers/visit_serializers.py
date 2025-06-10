from rest_framework import serializers
from ..models import VisitLog


class VisitLogSerializer(serializers.ModelSerializer):
    """Basic serializer for visit logs."""
    
    visit_type_display = serializers.CharField(source='get_visit_type_display', read_only=True)
    total_collected = serializers.ReadOnlyField()
    machine_info = serializers.SerializerMethodField()

    class Meta:
        model = VisitLog
        fields = [
            'id', 'placed_machine', 'machine_info', 'visit_date', 
            'visit_type', 'visit_type_display', 'notes', 'total_collected',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_machine_info(self, obj):
        """Get basic machine information."""
        return {
            'machine_type': obj.placed_machine.get_machine_type_display(),
            'location_name': obj.placed_machine.managed_location.location_name,
            'machine_identifier': obj.placed_machine.machine_identifier
        }


class VisitLogDetailSerializer(VisitLogSerializer):
    """Detailed serializer for visit logs with collection data."""
    
    collection_data = serializers.SerializerMethodField()
    
    class Meta(VisitLogSerializer.Meta):
        fields = VisitLogSerializer.Meta.fields + ['collection_data']
    
    def get_collection_data(self, obj):
        """Get collection data if exists."""
        if hasattr(obj, 'collection_data'):
            from .collection_serializers import CollectionDataSerializer
            return CollectionDataSerializer(obj.collection_data).data
        return None


class VisitLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating visit logs."""
    
    class Meta:
        model = VisitLog
        fields = [
            'placed_machine', 'visit_date', 'visit_type', 'notes'
        ]
    
    def validate_placed_machine(self, value):
        """Ensure user owns the machine."""
        user = self.context['request'].user
        if value.managed_location.user != user:
            raise serializers.ValidationError("You can only log visits to your own machines.")
        return value