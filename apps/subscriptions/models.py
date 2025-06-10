# from django.db import models
# from django.contrib.auth import get_user_model
# from django.core.validators import MinValueValidator, MaxValueValidator
# from django.utils import timezone
# from decimal import Decimal
# import uuid

# User = get_user_model()


from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()

# Rest of your models code stays the same...

class LeadCreditPackage(models.Model):
    """
    Model for add-on lead credit packages that users can purchase.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="Package name (e.g., 'Boost Pack')")
    description = models.TextField(help_text="Package description")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    lead_count = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        help_text="Number of leads included in this package"
    )
    target_buyer_plan = models.ForeignKey(
        'project_core.SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Target subscription plan (optional recommendation)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lead Credit Package'
        verbose_name_plural = 'Lead Credit Packages'
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.lead_count} leads (${self.price})"

    @property
    def price_per_lead(self):
        """Calculate price per lead."""
        return round(self.price / self.lead_count, 2)


class PaymentHistory(models.Model):
    """
    Model to track all payment transactions.
    """
    GATEWAY_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('manual', 'Manual'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_history'
    )
    subscription = models.ForeignKey(
        'project_core.UserSubscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Related subscription (for subscription payments)"
    )
    package_purchased = models.ForeignKey(
        LeadCreditPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Lead credit package purchased (for one-time purchases)"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    payment_gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    transaction_id = models.CharField(max_length=255, unique=True)
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment Histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['payment_gateway', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Payment {self.transaction_id} - ${self.amount} ({self.status})"

    def mark_completed(self, gateway_transaction_id=None):
        """Mark payment as completed."""
        self.status = 'completed'
        if gateway_transaction_id:
            self.gateway_transaction_id = gateway_transaction_id
        self.save(update_fields=['status', 'gateway_transaction_id', 'updated_at'])

    def mark_failed(self, reason=None):
        """Mark payment as failed."""
        self.status = 'failed'
        if reason:
            self.failure_reason = reason
        self.save(update_fields=['status', 'failure_reason', 'updated_at'])


class UserLeadCredit(models.Model):
    """
    Model to track user's additional lead credits from purchases.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lead_credits'
    )
    package = models.ForeignKey(
        LeadCreditPackage,
        on_delete=models.CASCADE
    )
    payment = models.ForeignKey(
        PaymentHistory,
        on_delete=models.CASCADE,
        related_name='lead_credits'
    )
    credits_purchased = models.IntegerField(validators=[MinValueValidator(1)])
    credits_used = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When these credits expire (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Lead Credit'
        verbose_name_plural = 'User Lead Credits'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.credits_remaining}/{self.credits_purchased} credits"

    @property
    def credits_remaining(self):
        """Calculate remaining credits."""
        return max(0, self.credits_purchased - self.credits_used)

    @property
    def is_expired(self):
        """Check if credits are expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def use_credits(self, amount=1):
        """Use credits and return success status."""
        if self.is_expired:
            return False
        
        if self.credits_remaining >= amount:
            self.credits_used += amount
            self.save(update_fields=['credits_used', 'updated_at'])
            return True
        return False


class SubscriptionUpgradeRequest(models.Model):
    """
    Model to track subscription upgrade/downgrade requests.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscription_requests'
    )
    current_subscription = models.ForeignKey(
        'project_core.UserSubscription',
        on_delete=models.CASCADE,
        related_name='upgrade_requests'
    )
    requested_plan = models.ForeignKey(
        'project_core.SubscriptionPlan',
        on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    proration_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Proration amount for upgrade/downgrade"
    )
    effective_date = models.DateTimeField(
        default=timezone.now,
        help_text="When the change should take effect"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription Upgrade Request'
        verbose_name_plural = 'Subscription Upgrade Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.current_subscription.plan.name} to {self.requested_plan.name}"


class SubscriptionCancellationRequest(models.Model):
    """
    Model to track subscription cancellation requests.
    """
    REASON_CHOICES = [
        ('too_expensive', 'Too Expensive'),
        ('not_enough_features', 'Not Enough Features'),
        ('technical_issues', 'Technical Issues'),
        ('switching_service', 'Switching to Another Service'),
        ('business_closure', 'Business Closure'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cancellation_requests'
    )
    subscription = models.ForeignKey(
        'project_core.UserSubscription',
        on_delete=models.CASCADE,
        related_name='cancellation_requests'
    )
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    feedback = models.TextField(blank=True, help_text="Additional feedback")
    cancel_immediately = models.BooleanField(
        default=False,
        help_text="Cancel immediately vs. at end of billing period"
    )
    cancellation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When cancellation will take effect"
    )
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription Cancellation Request'
        verbose_name_plural = 'Subscription Cancellation Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Cancellation: {self.user.email} - {self.subscription.plan.name}"