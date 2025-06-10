from rest_framework import serializers
from ..models import UserLocationPreference, SearchHistory


class UserLocationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user location preferences."""

    class Meta:
        model = UserLocationPreference
        fields = [
            'preferred_machine_types', 'preferred_radius', 'preferred_building_types',
            'excluded_categories', 'minimum_rating', 'require_contact_info',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_preferred_machine_types(self, value):
        """Validate machine types."""
        valid_types = [choice[0] for choice in SearchHistory.MACHINE_TYPE_CHOICES]
        for machine_type in value:
            if machine_type not in valid_types:
                raise serializers.ValidationError(f"Invalid machine type: {machine_type}")
        return value