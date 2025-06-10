from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import SupportTicket, WeatherLocation, SystemNotification, ContactMessage, SubscriptionPlan

User = get_user_model()


class SupportTicketSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'user_email', 'subject', 'description', 'priority', 
            'status', 'created_at', 'updated_at', 'resolved_at', 'is_open'
        ]
        read_only_fields = ['id', 'user', 'user_email', 'created_at', 'updated_at', 'resolved_at', 'is_open']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['subject', 'description', 'priority']

    def validate_subject(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Subject must be at least 5 characters long.")
        return value.strip()

    def validate_description(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError("Description must be at least 20 characters long.")
        return value.strip()


class WeatherLocationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    coordinates = serializers.ReadOnlyField()

    class Meta:
        model = WeatherLocation
        fields = [
            'id', 'user', 'address', 'zip_code', 'latitude', 'longitude',
            'city', 'state', 'country', 'coordinates', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'latitude', 'longitude', 'city', 'state', 'country', 'created_at', 'updated_at']

    def validate_zip_code(self, value):
        # Basic US ZIP code validation
        import re
        if not re.match(r'^\d{5}(-\d{4})?$', value):
            raise serializers.ValidationError("Invalid ZIP code format. Use 12345 or 12345-6789.")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SystemNotificationSerializer(serializers.ModelSerializer):
    is_current = serializers.ReadOnlyField()

    class Meta:
        model = SystemNotification
        fields = [
            'id', 'title', 'message', 'notification_type', 'is_active',
            'show_on_homepage', 'start_date', 'end_date', 'is_current', 'created_at'
        ]


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long.")
        return value.strip()

    def validate_subject(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Subject must be at least 5 characters long.")
        return value.strip()

    def validate_message(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError("Message must be at least 20 characters long.")
        return value.strip()

    def create(self, validated_data):
        # Add IP address and user agent from request
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        return super().create(validated_data)

    def get_client_ip(self, request):
        """Get the client's IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class WeatherDataSerializer(serializers.Serializer):
    """
    Serializer for weather data response.
    """
    location = serializers.CharField()
    temperature = serializers.FloatField()
    temperature_unit = serializers.CharField(default='F')
    description = serializers.CharField()
    humidity = serializers.IntegerField()
    wind_speed = serializers.FloatField()
    wind_unit = serializers.CharField(default='mph')
    icon = serializers.CharField()
    forecast = serializers.ListField(child=serializers.DictField(), required=False)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    is_free = serializers.ReadOnlyField()
    is_premium = serializers.ReadOnlyField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'price', 'leads_per_month', 'leads_per_search_range',
            'script_templates_count', 'regeneration_allowed', 'description',
            'is_free', 'is_premium'
        ]


class HomepageDataSerializer(serializers.Serializer):
    """
    Serializer for homepage data (public information).
    """
    company_name = serializers.CharField()
    tagline = serializers.CharField()
    features = serializers.ListField(child=serializers.DictField())
    subscription_plans = SubscriptionPlanSerializer(many=True)
    testimonials = serializers.ListField(child=serializers.DictField(), required=False)
    notifications = SystemNotificationSerializer(many=True, required=False)