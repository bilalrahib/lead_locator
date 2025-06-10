from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import SearchHistory, LocationData
from .location_serializers import LocationDataSerializer

User = get_user_model()


class LocationSearchSerializer(serializers.Serializer):
    """Serializer for location search requests."""
    
    zip_code = serializers.CharField(max_length=10)
    radius = serializers.ChoiceField(choices=SearchHistory.RADIUS_CHOICES, default=10)
    machine_type = serializers.ChoiceField(choices=SearchHistory.MACHINE_TYPE_CHOICES)
    building_types_filter = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )
    max_results = serializers.IntegerField(default=20, min_value=1, max_value=50)

    def validate_zip_code(self, value):
        """Validate ZIP code format."""
        import re
        if not re.match(r'^\d{5}(-\d{4})?$', value):
            raise serializers.ValidationError("Invalid ZIP code format. Use 12345 or 12345-6789.")
        return value

    def validate_building_types_filter(self, value):
        """Validate building types filter."""
        valid_types = [
            'churches', 'factories', 'hotels', 'rehabilitation_centers', 'gyms',
            'hospitals', 'towing_companies', 'laundromats', 'office_buildings',
            'industrial_facilities', 'daycares', 'ymcas', 'restaurants',
            'fast_food', 'barbershops', 'gas_stations', 'coffee_shops'
        ]
        
        for building_type in value:
            if building_type not in valid_types:
                raise serializers.ValidationError(f"Invalid building type: {building_type}")
        
        return value

    def validate(self, attrs):
        """Additional validation."""
        # Check user subscription limits
        user = self.context['request'].user
        
        if hasattr(user, 'subscription') and user.subscription and user.subscription.is_active:
            subscription = user.subscription
            if not subscription.can_search():
                if subscription.searches_used_this_period >= subscription.plan.leads_per_month:
                    raise serializers.ValidationError(
                        f"Monthly search limit reached ({subscription.plan.leads_per_month} searches). "
                        "Please upgrade your plan or wait for next billing cycle."
                    )
        else:
            # Check free tier limits (should be handled by subscription system)
            from django.utils import timezone
            from datetime import timedelta
            
            # For users without subscription, allow 3 searches per month
            current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_searches = SearchHistory.objects.filter(
                user=user,
                created_at__gte=current_month_start
            ).count()
            
            if monthly_searches >= 3:
                raise serializers.ValidationError(
                    "Free tier search limit reached (3 searches per month). "
                    "Please upgrade to a paid plan for more searches."
                )
        
        return attrs


class SearchHistorySerializer(serializers.ModelSerializer):
    """Serializer for search history."""
    
    machine_type_display = serializers.CharField(source='get_machine_type_display', read_only=True)
    search_summary = serializers.ReadOnlyField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = SearchHistory
        fields = [
            'id', 'user_email', 'zip_code', 'radius', 'machine_type',
            'machine_type_display', 'building_types_filter', 'results_count',
            'search_summary', 'search_parameters', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'machine_type_display', 'search_summary',
            'results_count', 'search_parameters', 'created_at'
        ]


class SearchHistoryDetailSerializer(SearchHistorySerializer):
    """Detailed serializer for search history with locations."""
    
    locations = LocationDataSerializer(many=True, read_only=True)

    class Meta(SearchHistorySerializer.Meta):
        fields = SearchHistorySerializer.Meta.fields + ['locations']