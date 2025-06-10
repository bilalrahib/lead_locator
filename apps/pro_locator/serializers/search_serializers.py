from rest_framework import serializers
from apps.locator.models import SearchHistory
from apps.locator.serializers import LocationSearchSerializer
from ..models import ClientProfile, ClientSavedSearch


class ClientSearchRequestSerializer(LocationSearchSerializer):
    """Serializer for client-specific search requests."""
    
    client_id = serializers.UUIDField()
    search_name = serializers.CharField(max_length=255)
    assign_to_client = serializers.BooleanField(default=True)
    client_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate_client_id(self, value):
        """Validate that client belongs to current user."""
        user = self.context['request'].user
        try:
            client = ClientProfile.objects.get(id=value, user=user, is_active=True)
            return value
        except ClientProfile.DoesNotExist:
            raise serializers.ValidationError("Client not found or not accessible.")

    def validate(self, attrs):
        """Additional validation for client searches."""
        attrs = super().validate(attrs)
        
        # Check if user has permission for client searches
        user = self.context['request'].user
        if not user.is_premium_user:
            raise serializers.ValidationError(
                "Client searches are only available for Elite and Professional plan users."
            )
        
        return attrs


class ClientSearchResultSerializer(serializers.Serializer):
    """Serializer for client search results."""
    
    search_history = serializers.SerializerMethodField()
    client_saved_search = serializers.SerializerMethodField()
    locations_assigned = serializers.IntegerField()
    message = serializers.CharField()

    def get_search_history(self, obj):
        """Get search history data."""
        from apps.locator.serializers import SearchHistoryDetailSerializer
        return SearchHistoryDetailSerializer(obj['search_history']).data

    def get_client_saved_search(self, obj):
        """Get client saved search data."""
        from .client_serializers import ClientSavedSearchSerializer
        return ClientSavedSearchSerializer(obj['client_saved_search']).data