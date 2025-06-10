from rest_framework import serializers
from ..models import LeadCreditPackage, UserLeadCredit


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