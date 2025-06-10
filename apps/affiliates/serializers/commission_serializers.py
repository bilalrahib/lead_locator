from rest_framework import serializers
from ..models import CommissionLedger


class CommissionLedgerSerializer(serializers.ModelSerializer):
    """Serializer for commission ledger entries."""
    
    affiliate_code = serializers.CharField(source='affiliate.referral_code', read_only=True)
    referred_user_email = serializers.EmailField(
        source='referred_user_subscription.user.email', 
        read_only=True
    )
    net_amount = serializers.ReadOnlyField()

    class Meta:
        model = CommissionLedger
        fields = [
            'id', 'affiliate_code', 'referred_user_email', 'subscription_amount',
            'commission_rate', 'amount_earned', 'net_amount', 'month_year',
            'status', 'paid_at', 'payout_method', 'created_at'
        ]
        read_only_fields = [
            'id', 'subscription_amount', 'commission_rate', 'amount_earned',
            'month_year', 'created_at'
        ]


class EarningsSummarySerializer(serializers.Serializer):
    """Serializer for earnings summary."""
    
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    this_month_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    last_month_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_conversions = serializers.IntegerField()
    active_referrals = serializers.IntegerField()
    conversion_rate = serializers.FloatField()


class PayoutReportSerializer(serializers.Serializer):
    """Serializer for payout reports."""
    
    period = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    commission_count = serializers.IntegerField()
    status = serializers.CharField()
    payout_method = serializers.CharField()
    created_date = serializers.DateTimeField()