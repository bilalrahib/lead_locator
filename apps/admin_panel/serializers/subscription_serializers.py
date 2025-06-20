from rest_framework import serializers
from apps.project_core.models import SubscriptionPlan
from apps.subscriptions.models import LeadCreditPackage


class AdminSubscriptionPlanSerializer(serializers.ModelSerializer):
    """Admin serializer for subscription plans."""
    
    user_count = serializers.SerializerMethodField()
    revenue_generated = serializers.SerializerMethodField()
    is_free = serializers.ReadOnlyField()
    is_premium = serializers.ReadOnlyField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'price', 'leads_per_month', 'leads_per_search_range',
            'script_templates_count', 'regeneration_allowed', 'description',
            'is_active', 'is_free', 'is_premium', 'user_count',
            'revenue_generated', 'created_at', 'updated_at'
        ]

    def get_user_count(self, obj):
        """Get number of users on this plan."""
        return obj.subscriptions.filter(is_active=True).count()

    def get_revenue_generated(self, obj):
        """Get revenue generated by this plan."""
        from django.db.models import Sum
        from apps.subscriptions.models import PaymentHistory
        
        revenue = PaymentHistory.objects.filter(
            subscription__plan=obj,
            status='completed'
        ).aggregate(total=Sum('amount'))['total']
        
        return revenue or 0


class AdminLeadCreditPackageSerializer(serializers.ModelSerializer):
    """Admin serializer for lead credit packages."""
    
    price_per_lead = serializers.ReadOnlyField()
    purchase_count = serializers.SerializerMethodField()
    revenue_generated = serializers.SerializerMethodField()
    target_plan_name = serializers.CharField(source='target_buyer_plan.name', read_only=True)

    class Meta:
        model = LeadCreditPackage
        fields = [
            'id', 'name', 'description', 'price', 'lead_count',
            'price_per_lead', 'target_buyer_plan', 'target_plan_name',
            'is_active', 'purchase_count', 'revenue_generated',
            'created_at', 'updated_at'
        ]

    def get_purchase_count(self, obj):
        """Get number of times this package was purchased."""
        return obj.userleadcredit_set.count()

    def get_revenue_generated(self, obj):
        """Get revenue generated by this package."""
        from django.db.models import Sum
        from apps.subscriptions.models import PaymentHistory
        
        revenue = PaymentHistory.objects.filter(
            package_purchased=obj,
            status='completed'
        ).aggregate(total=Sum('amount'))['total']
        
        return revenue or 0


class SubscriptionAnalyticsSerializer(serializers.Serializer):
    """Serializer for subscription analytics."""
    
    total_subscriptions = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()
    plan_distribution = serializers.DictField()
    monthly_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    churn_rate = serializers.FloatField()
    upgrade_rate = serializers.FloatField()
    average_revenue_per_user = serializers.DecimalField(max_digits=10, decimal_places=2)
    subscription_growth = serializers.DictField()