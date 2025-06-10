from rest_framework import serializers
from ..models import LocationData


class LocationDataSerializer(serializers.ModelSerializer):
    """Serializer for location data."""
    
    foot_traffic_display = serializers.CharField(source='get_foot_traffic_estimate_display', read_only=True)
    contact_completeness_display = serializers.CharField(source='get_contact_completeness_display', read_only=True)
    coordinates = serializers.ReadOnlyField()

    class Meta:
        model = LocationData
        fields = [
            'id', 'name', 'category', 'detailed_category', 'address',
            'latitude', 'longitude', 'coordinates', 'phone', 'email', 'website',
            'business_hours_text', 'google_place_id', 'google_rating',
            'google_user_ratings_total', 'google_business_status', 'maps_url',
            'foot_traffic_estimate', 'foot_traffic_display', 'priority_score',
            'contact_completeness', 'contact_completeness_display', 'created_at'
        ]
        read_only_fields = [
            'id', 'coordinates', 'foot_traffic_display', 'contact_completeness_display',
            'priority_score', 'contact_completeness', 'created_at'
        ]