from rest_framework import serializers
from ..models import ExcludedLocation


class ExcludedLocationSerializer(serializers.ModelSerializer):
    """Serializer for excluded locations."""
    
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)

    class Meta:
        model = ExcludedLocation
        fields = [
            'id', 'google_place_id', 'location_name', 'reason',
            'reason_display', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'reason_display', 'created_at']

    def create(self, validated_data):
        """Create excluded location."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)