from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.locator.models import SearchHistory
from ..models import ClientProfile, ClientSavedSearch, ClientLocationData
from django.db import models  # Add this import

User = get_user_model()


class ClientProfileSerializer(serializers.ModelSerializer):
    """Serializer for client profile basic information."""
    
    total_searches = serializers.ReadOnlyField()
    total_locations_found = serializers.ReadOnlyField()
    default_machine_type_display = serializers.CharField(
        source='get_default_machine_type_display', read_only=True
    )

    class Meta:
        model = ClientProfile
        fields = [
            'id', 'client_name', 'client_contact_name', 'client_email', 'client_phone',
            'client_zip_code', 'client_city', 'client_state', 'default_machine_type',
            'default_machine_type_display', 'client_notes', 'is_active',
            'total_searches', 'total_locations_found', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_searches', 'total_locations_found', 'created_at', 'updated_at'
        ]


class ClientProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating client profiles."""

    class Meta:
        model = ClientProfile
        fields = [
            'client_name', 'client_contact_name', 'client_email', 'client_phone',
            'client_zip_code', 'client_city', 'client_state', 'default_machine_type',
            'client_notes', 'is_active'
        ]

    def validate_client_zip_code(self, value):
        """Validate ZIP code format."""
        import re
        if not re.match(r'^\d{5}(-\d{4})?$', value):
            raise serializers.ValidationError("Invalid ZIP code format. Use 12345 or 12345-6789.")
        return value

    def validate_client_phone(self, value):
        """Validate phone number format."""
        if value:
            import re
            digits = re.sub(r'\D', '', value)
            if len(digits) < 10 or len(digits) > 15:
                raise serializers.ValidationError(
                    "Phone number must be between 10 and 15 digits."
                )
        return value

    def create(self, validated_data):
        """Create client profile with current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ClientProfileDetailSerializer(ClientProfileSerializer):
    """Detailed serializer for client profiles with related data."""
    
    recent_searches = serializers.SerializerMethodField()
    location_stats = serializers.SerializerMethodField()

    class Meta(ClientProfileSerializer.Meta):
        fields = ClientProfileSerializer.Meta.fields + ['recent_searches', 'location_stats']

    def get_recent_searches(self, obj):
        """Get recent searches for this client."""
        recent_searches = obj.saved_searches.order_by('-created_at')[:5]
        return ClientSavedSearchSerializer(recent_searches, many=True).data

    def get_location_stats(self, obj):
        """Get location statistics for this client."""
        from django.db.models import Count
        
        stats = obj.client_locations.aggregate(
            total=Count('id'),
            new=Count('id', filter=models.Q(status='new')),
            contacted=Count('id', filter=models.Q(status='contacted')),
            interested=Count('id', filter=models.Q(status='interested')),
            placed=Count('id', filter=models.Q(status='placed'))
        )
        
        return {
            'total_locations': stats['total'] or 0,
            'new_leads': stats['new'] or 0,
            'contacted': stats['contacted'] or 0,
            'interested': stats['interested'] or 0,
            'machines_placed': stats['placed'] or 0
        }


class ClientSavedSearchSerializer(serializers.ModelSerializer):
    """Serializer for client saved searches."""
    
    client_name = serializers.CharField(source='client_profile.client_name', read_only=True)
    search_summary = serializers.CharField(source='search_history.search_summary', read_only=True)
    results_count = serializers.IntegerField(source='search_history.results_count', read_only=True)
    locations_assigned_count = serializers.SerializerMethodField()

    class Meta:
        model = ClientSavedSearch
        fields = [
            'id', 'client_name', 'search_name', 'search_summary', 'results_count',
            'locations_assigned_count', 'notes', 'is_shared_with_client', 'shared_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'client_name', 'search_summary', 'results_count',
            'locations_assigned_count', 'shared_at', 'created_at', 'updated_at'
        ]

    def get_locations_assigned_count(self, obj):
        """Get count of locations assigned to client from this search."""
        return obj.assigned_locations.count()


class ClientLocationDataSerializer(serializers.ModelSerializer):
    """Serializer for client location assignments."""
    
    location_name = serializers.CharField(source='location_data.name', read_only=True)
    location_address = serializers.CharField(source='location_data.address', read_only=True)
    location_phone = serializers.CharField(source='location_data.phone', read_only=True)
    location_email = serializers.CharField(source='location_data.email', read_only=True)
    location_rating = serializers.DecimalField(
        source='location_data.google_rating', read_only=True, max_digits=3, decimal_places=2
    )
    priority_score = serializers.IntegerField(source='location_data.priority_score', read_only=True)
    client_name = serializers.CharField(source='client_profile.client_name', read_only=True)
    search_name = serializers.CharField(source='saved_search.search_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ClientLocationData
        fields = [
            'id', 'client_name', 'search_name', 'location_name', 'location_address',
            'location_phone', 'location_email', 'location_rating', 'priority_score',
            'notes', 'priority', 'status', 'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'client_name', 'search_name', 'location_name', 'location_address',
            'location_phone', 'location_email', 'location_rating', 'priority_score',
            'status_display', 'created_at', 'updated_at'
        ]


class ClientLocationDataUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating client location data."""

    class Meta:
        model = ClientLocationData
        fields = ['notes', 'priority', 'status']

    def validate_priority(self, value):
        """Validate priority range."""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Priority must be between 0 and 100.")
        return value