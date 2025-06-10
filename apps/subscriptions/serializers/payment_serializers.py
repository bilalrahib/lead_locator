from rest_framework import serializers
from ..models import PaymentHistory


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for payment history."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    subscription_plan = serializers.CharField(source='subscription.plan.name', read_only=True)
    package_name = serializers.CharField(source='package_purchased.name', read_only=True)

    class Meta:
        model = PaymentHistory
        fields = [
            'id', 'user_email', 'amount', 'currency', 'payment_gateway',
            'transaction_id', 'status', 'subscription_plan', 'package_name',
            'created_at'
        ]
        read_only_fields = fields


class WebhookEventSerializer(serializers.Serializer):
    """Serializer for webhook events."""
    
    event_type = serializers.CharField()
    event_id = serializers.CharField()
    data = serializers.DictField()