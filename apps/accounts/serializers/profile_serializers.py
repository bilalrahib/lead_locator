from rest_framework import serializers
from ..models import UserProfile, UserActivity


class UserProfileDetailSerializer(serializers.ModelSerializer):
    """Detailed user profile serializer."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    completion_percentage = serializers.ReadOnlyField()
    full_address = serializers.ReadOnlyField()

    class Meta:
        model = UserProfile
        fields = [
            'user_email', 'user_name', 'business_type', 'years_in_business',
            'number_of_machines', 'target_locations', 'address_line1',
            'address_line2', 'city', 'state', 'zip_code', 'country',
            'linkedin_url', 'twitter_url', 'facebook_url',
            'preferred_contact_method', 'profile_completed',
            'completion_percentage', 'full_address', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user_email', 'user_name', 'completion_percentage', 'full_address',
            'profile_completed', 'created_at', 'updated_at'
        ]


class UserProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating user profile."""

    class Meta:
        model = UserProfile
        fields = [
            'business_type', 'years_in_business', 'number_of_machines',
            'target_locations', 'address_line1', 'address_line2',
            'city', 'state', 'zip_code', 'country', 'linkedin_url',
            'twitter_url', 'facebook_url', 'preferred_contact_method'
        ]

    def validate_years_in_business(self, value):
        """Validate years in business."""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError(
                "Years in business must be between 0 and 100."
            )
        return value

    def validate_number_of_machines(self, value):
        """Validate number of machines."""
        if value is not None and (value < 0 or value > 10000):
            raise serializers.ValidationError(
                "Number of machines must be between 0 and 10,000."
            )
        return value

    def validate_zip_code(self, value):
        """Validate ZIP code format."""
        if value:
            import re
            if not re.match(r'^\d{5}(-\d{4})?$', value):
                raise serializers.ValidationError(
                    "ZIP code must be in format 12345 or 12345-6789."
                )
        return value

    def create(self, validated_data):
        """Create user profile."""
        user = self.context['request'].user
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults=validated_data
        )
        if not created:
            # Update existing profile
            for attr, value in validated_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        # Check if profile is now complete
        if profile.completion_percentage >= 80:
            profile.mark_completed()
        
        return profile


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for user activities."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    activity_display = serializers.CharField(source='get_activity_type_display', read_only=True)

    class Meta:
        model = UserActivity
        fields = [
            'id', 'user_email', 'activity_type', 'activity_display',
            'description', 'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics."""
    
    total_searches = serializers.IntegerField()
    total_scripts = serializers.IntegerField()
    total_tickets = serializers.IntegerField()
    account_age_days = serializers.IntegerField()
    last_activity = serializers.DateTimeField()
    subscription_plan = serializers.CharField()
    profile_completion = serializers.IntegerField()