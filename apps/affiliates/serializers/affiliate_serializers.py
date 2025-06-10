from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import AffiliateProfile, ReferralClick, ReferralConversion, AffiliateResource

User = get_user_model()


class AffiliateApplicationSerializer(serializers.ModelSerializer):
    """Serializer for affiliate application."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = AffiliateProfile
        fields = [
            'user_email', 'user_name', 'website_url', 'application_reason',
            'marketing_experience', 'traffic_sources', 'created_at'
        ]
        read_only_fields = ['user_email', 'user_name', 'created_at']

    def validate_website_url(self, value):
        """Validate website URL."""
        if value and not value.startswith(('http://', 'https://')):
            value = 'https://' + value
        return value

    def create(self, validated_data):
        """Create affiliate application."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AffiliateProfileSerializer(serializers.ModelSerializer):
    """Serializer for affiliate profile details."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    referral_url = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    total_earnings = serializers.SerializerMethodField()
    pending_earnings = serializers.SerializerMethodField()
    total_conversions = serializers.SerializerMethodField()

    class Meta:
        model = AffiliateProfile
        fields = [
            'id', 'user_email', 'user_name', 'referral_code', 'referral_url',
            'status', 'is_active', 'website_url', 'commission_rate',
            'minimum_payout', 'total_earnings', 'pending_earnings',
            'total_conversions', 'approved_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'referral_code', 'status', 'commission_rate',
            'approved_at', 'created_at'
        ]

    def get_total_earnings(self, obj):
        """Get total earnings."""
        return float(obj.get_total_earnings())

    def get_pending_earnings(self, obj):
        """Get pending earnings."""
        return float(obj.get_pending_earnings())

    def get_total_conversions(self, obj):
        """Get total conversions."""
        return obj.conversions.count()


class PayoutInfoSerializer(serializers.ModelSerializer):
    """Serializer for updating payout information."""
    
    class Meta:
        model = AffiliateProfile
        fields = [
            'payout_method', 'paypal_email', 'stripe_connect_id',
            'minimum_payout'
        ]

    def validate_paypal_email(self, value):
        """Validate PayPal email if PayPal is selected."""
        payout_method = self.initial_data.get('payout_method')
        if payout_method == 'paypal' and not value:
            raise serializers.ValidationError("PayPal email is required for PayPal payouts.")
        return value

    def validate_stripe_connect_id(self, value):
        """Validate Stripe Connect ID if Stripe is selected."""
        payout_method = self.initial_data.get('payout_method')
        if payout_method == 'stripe' and not value:
            raise serializers.ValidationError("Stripe Connect ID is required for Stripe payouts.")
        return value


class ReferralClickSerializer(serializers.ModelSerializer):
    """Serializer for referral clicks."""
    
    affiliate_code = serializers.CharField(source='affiliate.referral_code', read_only=True)

    class Meta:
        model = ReferralClick
        fields = [
            'id', 'affiliate_code', 'ip_address', 'referrer_url',
            'landing_page', 'timestamp'
        ]


class ReferralConversionSerializer(serializers.ModelSerializer):
    """Serializer for referral conversions."""
    
    affiliate_code = serializers.CharField(source='affiliate.referral_code', read_only=True)
    referred_user_email = serializers.EmailField(source='referred_user.email', read_only=True)
    referred_user_name = serializers.CharField(source='referred_user.full_name', read_only=True)

    class Meta:
        model = ReferralConversion
        fields = [
            'id', 'affiliate_code', 'referred_user_email', 'referred_user_name',
            'conversion_value', 'timestamp'
        ]


class AffiliateResourceSerializer(serializers.ModelSerializer):
    """Serializer for affiliate resources."""
    
    class Meta:
        model = AffiliateResource
        fields = [
            'id', 'title', 'description', 'resource_type', 'file_url',
            'thumbnail_url', 'download_count', 'created_at'
        ]
        read_only_fields = ['id', 'download_count', 'created_at']


class AffiliateDashboardSerializer(serializers.Serializer):
    """Serializer for affiliate dashboard data."""
    
    profile = AffiliateProfileSerializer()
    recent_clicks = ReferralClickSerializer(many=True)
    recent_conversions = ReferralConversionSerializer(many=True)
    earnings_summary = serializers.DictField()
    performance_metrics = serializers.DictField()
    available_resources = AffiliateResourceSerializer(many=True)