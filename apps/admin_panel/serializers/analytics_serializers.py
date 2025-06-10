from rest_framework import serializers
from ..models import AdminDashboardStats


class DashboardStatsSerializer(serializers.ModelSerializer):
    """Serializer for dashboard statistics."""
    
    class Meta:
        model = AdminDashboardStats
        fields = [
            'stat_date', 'total_users', 'new_users_today',
            'active_subscriptions', 'revenue_today', 'searches_today',
            'support_tickets_open', 'cache_data'
        ]


class UserAnalyticsSerializer(serializers.Serializer):
    """Serializer for user analytics."""
    
    total_users = serializers.IntegerField()
    new_users_this_month = serializers.IntegerField()
    active_users_this_month = serializers.IntegerField()
    user_growth_rate = serializers.FloatField()
    top_countries = serializers.ListField()
    user_by_plan = serializers.DictField()
    email_verification_rate = serializers.FloatField()
    user_retention_rate = serializers.FloatField()


class RevenueAnalyticsSerializer(serializers.Serializer):
    """Serializer for revenue analytics."""
    
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_growth_rate = serializers.FloatField()
    revenue_by_plan = serializers.DictField()
    revenue_trend = serializers.ListField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)


class UsageAnalyticsSerializer(serializers.Serializer):
    """Serializer for usage analytics."""
    
    total_searches = serializers.IntegerField()
    searches_this_month = serializers.IntegerField()
    average_searches_per_user = serializers.FloatField()
    popular_search_locations = serializers.ListField()
    usage_by_plan = serializers.DictField()
    peak_usage_hours = serializers.ListField()


class SystemAnalyticsSerializer(serializers.Serializer):
    """Serializer for system analytics."""
    
    api_requests_today = serializers.IntegerField()
    error_rate = serializers.FloatField()
    average_response_time = serializers.FloatField()
    system_uptime = serializers.FloatField()
    database_size = serializers.CharField()
    active_sessions = serializers.IntegerField()