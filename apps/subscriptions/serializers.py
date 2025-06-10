from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.project_core.models import SubscriptionPlan, UserSubscription
from .models import (
    LeadCreditPackage, PaymentHistory, UserLeadCredit,
    SubscriptionUpgradeRequest, SubscriptionCancellationRequest
)

User = get_user_model()


class SubscriptionPlanDetailSerializer(serializers.ModelSerializer):
    """Enhanced subscription plan serializer with additional details."""
    
    is_free = serializers.ReadOnlyField()
    is_premium = serializers.ReadOnlyField()
    features = serializers.SerializerMethodField()
    popular = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'price', 'leads_per_month', 'leads_per_search_range',
            'script_templates_count', 'regeneration_allowed', 'description',
            'is_free', 'is_premium', 'features', 'popular'
        ]

    def get_features(self, obj):
        """Get formatted feature list for the plan."""
        features = [
            f"{obj.leads_per_month} leads per month",
            f"{obj.leads_per_search_range} leads per search",
            f"{obj.script_templates_count} script templates" if obj.script_templates_count < 999 else "Unlimited script templates",
        ]
        
        if obj.regeneration_allowed:
            features.append("Script regeneration")
        
        if obj.name in ['ELITE', 'PROFESSIONAL']:
            features.extend([
                "Priority support",
                "Advanced analytics",
                "Pro dashboard access"
            ])
        
        if obj.name == 'PROFESSIONAL':
            features.extend([
                "White-label options",
                "Client management tools",
                "Bulk operations"
            ])
        
        return features

    def get_popular(self, obj):
        """Mark popular plans."""
        return obj.name in ['PRO', 'ELITE']


class LeadCreditPackageSerializer(serializers.ModelSerializer):
    """Serializer for lead credit packages."""
    
    price_per_lead = serializers.ReadOnlyField()
    target_plan_name = serializers.CharField(source='target_buyer_plan.name', read_only=True)

    class Meta:
        model = LeadCreditPackage
        fields = [
            'id', 'name', 'description', 'price', 'lead_count',
            'price_per_lead', 'target_buyer_plan', 'target_plan_name', 'is_active'
        ]


class UserSubscriptionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for user subscriptions."""
    
    plan_details = SubscriptionPlanDetailSerializer(source='plan', read_only=True)
    is_expired = serializers.ReadOnlyField()
    searches_left = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    next_billing_date = serializers.SerializerMethodField()

    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan_details', 'start_date', 'end_date', 'is_active',
            'is_expired', 'searches_used_this_period', 'searches_left',
            'days_remaining', 'next_billing_date', 'stripe_subscription_id',
            'created_at'
        ]
        read_only_fields = [
            'id', 'searches_used_this_period', 'stripe_subscription_id', 'created_at'
        ]

    def get_searches_left(self, obj):
        """Get remaining searches for current period."""
        return obj.searches_left_this_period()

    def get_days_remaining(self, obj):
        """Get days remaining in current billing period."""
        if not obj.end_date:
            return None
        from django.utils import timezone
        delta = obj.end_date - timezone.now()
        return max(0, delta.days)

    def get_next_billing_date(self, obj):
        """Get next billing date."""
        return obj.end_date


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


class UserLeadCreditSerializer(serializers.ModelSerializer):
    """Serializer for user lead credits."""
    
    package_name = serializers.CharField(source='package.name', read_only=True)
    credits_remaining = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = UserLeadCredit
        fields = [
            'id', 'package_name', 'credits_purchased', 'credits_used',
            'credits_remaining', 'expires_at', 'is_expired', 'created_at'
        ]
        read_only_fields = fields


class SubscriptionCreateSerializer(serializers.Serializer):
    """Serializer for creating new subscriptions."""
    
    plan_id = serializers.IntegerField()
    payment_method_id = serializers.CharField(required=False)
    billing_address = serializers.DictField(required=False)

    def validate_plan_id(self, value):
        """Validate that the plan exists and is active."""
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
            return value
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive subscription plan.")

    def validate(self, attrs):
        """Additional validation."""
        user = self.context['request'].user
        
        # Check if user already has an active subscription
        if hasattr(user, 'subscription') and user.subscription.is_active:
            raise serializers.ValidationError(
                "You already have an active subscription. Please cancel it first or use the upgrade endpoint."
            )
        
        return attrs


class PackagePurchaseSerializer(serializers.Serializer):
    """Serializer for purchasing lead credit packages."""
    
    package_id = serializers.UUIDField()
    payment_method_id = serializers.CharField(required=False)

    def validate_package_id(self, value):
        """Validate that the package exists and is active."""
        try:
            package = LeadCreditPackage.objects.get(id=value, is_active=True)
            return value
        except LeadCreditPackage.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive lead credit package.")


class SubscriptionUpgradeSerializer(serializers.Serializer):
    """Serializer for subscription upgrades/downgrades."""
    
    new_plan_id = serializers.IntegerField()
    effective_immediately = serializers.BooleanField(default=True)

    def validate_new_plan_id(self, value):
        """Validate the new plan."""
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
            return value
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive subscription plan.")

    def validate(self, attrs):
        """Validate upgrade request."""
        user = self.context['request'].user
        
        if not hasattr(user, 'subscription') or not user.subscription.is_active:
            raise serializers.ValidationError("No active subscription found.")
        
        new_plan = SubscriptionPlan.objects.get(id=attrs['new_plan_id'])
        current_plan = user.subscription.plan
        
        if new_plan.id == current_plan.id:
            raise serializers.ValidationError("Cannot upgrade to the same plan.")
        
        return attrs


class SubscriptionCancellationSerializer(serializers.ModelSerializer):
    """Serializer for subscription cancellations."""
    
    class Meta:
        model = SubscriptionCancellationRequest
        fields = ['reason', 'feedback', 'cancel_immediately']

    def validate(self, attrs):
        """Validate cancellation request."""
        user = self.context['request'].user
        
        if not hasattr(user, 'subscription') or not user.subscription.is_active:
            raise serializers.ValidationError("No active subscription found to cancel.")
        
        return attrs

    def create(self, validated_data):
        """Create cancellation request."""
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['subscription'] = user.subscription
        
        return super().create(validated_data)


class WebhookEventSerializer(serializers.Serializer):
    """Serializer for webhook events."""
    
    event_type = serializers.CharField()
    event_id = serializers.CharField()
    data = serializers.DictField()


class UsageStatsSerializer(serializers.Serializer):
    """Serializer for subscription usage statistics."""
    
    current_plan = serializers.CharField()
    searches_used = serializers.IntegerField()
    searches_limit = serializers.IntegerField()
    searches_remaining = serializers.IntegerField()
    additional_credits = serializers.IntegerField()
    billing_period_start = serializers.DateTimeField()
    billing_period_end = serializers.DateTimeField()
    next_reset_date = serializers.DateTimeField()


class BillingHistorySerializer(serializers.Serializer):
    """Serializer for billing history summary."""
    
    payments = PaymentHistorySerializer(many=True)
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2)
    subscription_payments = serializers.IntegerField()
    package_purchases = serializers.IntegerField()