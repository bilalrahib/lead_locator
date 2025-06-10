from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.project_core.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.models import LeadCreditPackage

User = get_user_model()


class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer for user list in admin panel."""
    
    full_name = serializers.ReadOnlyField()
    subscription_status = serializers.ReadOnlyField()
    profile_completion = serializers.SerializerMethodField()
    last_activity_display = serializers.SerializerMethodField()
    total_searches = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'full_name', 'phone', 'company_name',
            'is_active', 'is_staff', 'email_verified', 'subscription_status',
            'profile_completion', 'date_joined', 'last_login', 'last_activity',
            'last_activity_display', 'total_searches'
        ]

    def get_profile_completion(self, obj):
        """Get profile completion percentage."""
        try:
            return obj.profile.completion_percentage
        except:
            return 0

    def get_last_activity_display(self, obj):
        """Get formatted last activity."""
        if obj.last_activity:
            from django.utils import timezone
            delta = timezone.now() - obj.last_activity
            if delta.days > 0:
                return f"{delta.days} days ago"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours} hours ago"
            elif delta.seconds > 60:
                minutes = delta.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return "Just now"
        return "Never"

    def get_total_searches(self, obj):
        """Get total searches performed by user."""
        # This would be implemented when locator app is available
        return 0


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for user in admin panel."""
    
    full_name = serializers.ReadOnlyField()
    subscription_details = serializers.SerializerMethodField()
    profile_details = serializers.SerializerMethodField()
    activity_stats = serializers.SerializerMethodField()
    payment_stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone', 'company_name', 'website', 'bio', 'is_active', 'is_staff',
            'is_superuser', 'email_verified', 'subscription_details',
            'profile_details', 'activity_stats', 'payment_stats',
            'date_joined', 'last_login', 'last_activity', 'failed_login_attempts',
            'is_locked', 'email_notifications', 'marketing_emails'
        ]
        read_only_fields = [
            'id', 'date_joined', 'last_login', 'last_activity',
            'failed_login_attempts', 'is_locked'
        ]

    def get_subscription_details(self, obj):
        """Get subscription details."""
        if hasattr(obj, 'subscription') and obj.subscription:
            subscription = obj.subscription
            return {
                'plan_name': subscription.plan.name,
                'plan_price': subscription.plan.price,
                'start_date': subscription.start_date,
                'end_date': subscription.end_date,
                'is_active': subscription.is_active,
                'searches_used': subscription.searches_used_this_period,
                'searches_limit': subscription.plan.leads_per_month
            }
        return None

    def get_profile_details(self, obj):
        """Get profile details."""
        try:
            profile = obj.profile
            return {
                'business_type': profile.business_type,
                'years_in_business': profile.years_in_business,
                'number_of_machines': profile.number_of_machines,
                'completion_percentage': profile.completion_percentage,
                'profile_completed': profile.profile_completed,
                'city': profile.city,
                'state': profile.state,
                'country': profile.country
            }
        except:
            return None

    def get_activity_stats(self, obj):
        """Get activity statistics."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Recent activities (last 30 days)
        recent_activities = obj.activities.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return {
            'total_activities': obj.activities.count(),
            'recent_activities': recent_activities,
            'total_support_tickets': obj.support_tickets.count(),
            'open_support_tickets': obj.support_tickets.filter(status='open').count()
        }

    def get_payment_stats(self, obj):
        """Get payment statistics."""
        from django.db.models import Sum
        from apps.subscriptions.models import PaymentHistory
        
        payments = PaymentHistory.objects.filter(user=obj, status='completed')
        
        return {
            'total_spent': payments.aggregate(total=Sum('amount'))['total'] or 0,
            'total_payments': payments.count(),
            'subscription_payments': payments.filter(subscription__isnull=False).count(),
            'package_purchases': payments.filter(package_purchased__isnull=False).count()
        }


class UserActivationSerializer(serializers.Serializer):
    """Serializer for user activation/deactivation."""
    
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=['activate', 'deactivate'])
    reason = serializers.CharField(max_length=500, required=False)

    def validate_user_ids(self, value):
        """Validate that all user IDs exist."""
        existing_users = User.objects.filter(id__in=value).count()
        if existing_users != len(value):
            raise serializers.ValidationError("Some user IDs are invalid.")
        return value


class UserSubscriptionChangeSerializer(serializers.Serializer):
    """Serializer for changing user subscriptions."""
    
    user_id = serializers.UUIDField()
    new_plan_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=500, required=False)
    effective_immediately = serializers.BooleanField(default=True)

    def validate_user_id(self, value):
        """Validate user exists."""
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found.")
        return value

    def validate_new_plan_id(self, value):
        """Validate plan exists."""
        if not SubscriptionPlan.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid subscription plan.")
        return value


class BulkUserActionSerializer(serializers.Serializer):
    """Serializer for bulk user actions."""
    
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100  # Limit bulk operations
    )
    action = serializers.ChoiceField(choices=[
        'activate', 'deactivate', 'verify_email', 'reset_password',
        'unlock_account', 'grant_credits'
    ])
    parameters = serializers.DictField(required=False)

    def validate_user_ids(self, value):
        """Validate user IDs."""
        existing_users = User.objects.filter(id__in=value).count()
        if existing_users != len(value):
            raise serializers.ValidationError("Some user IDs are invalid.")
        return value

    def validate(self, attrs):
        """Validate action-specific parameters."""
        action = attrs['action']
        parameters = attrs.get('parameters', {})

        if action == 'grant_credits':
            if 'package_id' not in parameters:
                raise serializers.ValidationError("package_id required for grant_credits action.")
            
            try:
                LeadCreditPackage.objects.get(id=parameters['package_id'])
            except LeadCreditPackage.DoesNotExist:
                raise serializers.ValidationError("Invalid package_id.")

        return attrs