from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator, URLValidator
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
import uuid
import string
import random

User = get_user_model()


class AffiliateProfile(models.Model):
    """
    Profile for affiliate users with referral tracking and payout information.
    """
    PAYOUT_METHODS = [
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe Connect'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='affiliate_profile'
    )
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique referral code for the affiliate"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    website_url = models.URLField(
        blank=True,
        validators=[URLValidator()],
        help_text="Affiliate's website or social media profile"
    )
    
    # Payout Information (encrypted in production)
    payout_method = models.CharField(
        max_length=20,
        choices=PAYOUT_METHODS,
        default='paypal'
    )
    paypal_email = models.EmailField(
        blank=True,
        validators=[EmailValidator()],
        help_text="PayPal email for payouts"
    )
    stripe_connect_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Stripe Connect account ID"
    )
    bank_account_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Encrypted bank account details"
    )
    
    # Commission Settings
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('30.00'),
        help_text="Commission rate as percentage (default 30%)"
    )
    minimum_payout = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text="Minimum amount required for payout"
    )
    
    # Application Information
    application_reason = models.TextField(
        help_text="Reason for wanting to become an affiliate"
    )
    marketing_experience = models.TextField(
        blank=True,
        help_text="Previous marketing or affiliate experience"
    )
    traffic_sources = models.TextField(
        blank=True,
        help_text="Where affiliate plans to promote (social media, website, etc.)"
    )
    
    # Status Tracking
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_affiliates'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Affiliate Profile'
        verbose_name_plural = 'Affiliate Profiles'
        indexes = [
            models.Index(fields=['referral_code']),
            models.Index(fields=['status', 'approved_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.referral_code}"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_referral_code():
        """Generate unique referral code."""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not AffiliateProfile.objects.filter(referral_code=code).exists():
                return code

    @property
    def referral_url(self):
        """Get full referral URL."""
        from django.conf import settings
        base_url = getattr(settings, 'FRONTEND_URL', 'https://vendinghive.com')
        return f"{base_url}/?ref={self.referral_code}"

    @property
    def is_active(self):
        """Check if affiliate is active."""
        return self.status == 'approved'

    # def approve(self, admin_user):
    #     """Approve affiliate application."""
    #     self.status = 'approved'
    #     self.approved_at = timezone.now()
    #     self.approved_by = admin_user
    #     self.save()
        
    #     # Update user's affiliate status
    #     self.user.is_approved_affiliate = True
    #     self.user.save(update_fields=['is_approved_affiliate'])

    def approve(self, admin_user):
        """Approve affiliate application."""
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = admin_user
        self.save()
        
        # Update user's affiliate status - NO update_fields to avoid tracker conflict
        self.user.is_approved_affiliate = True
        self.user.save()  # REMOVE any update_fields parameter


    def reject(self):
        """Reject affiliate application."""
        self.status = 'rejected'
        self.save()

    # def suspend(self):
    #     """Suspend affiliate."""
    #     self.status = 'suspended'
    #     self.save()
        
    #     # Update user's affiliate status
    #     self.user.is_approved_affiliate = False
    #     self.user.save(update_fields=['is_approved_affiliate'])
    def suspend(self):
        """Suspend affiliate."""
        self.status = 'suspended'
        self.save()
        
        # Update user's affiliate status - NO update_fields to avoid tracker conflict
        self.user.is_approved_affiliate = False
        self.user.save()  # REMOVE any update_fields parameter

    def get_total_earnings(self):
        """Get total earnings for this affiliate."""
        return self.commission_ledger.filter(
            status='paid'
        ).aggregate(
            total=models.Sum('amount_earned')
        )['total'] or Decimal('0.00')

    def get_pending_earnings(self):
        """Get pending earnings for this affiliate."""
        return self.commission_ledger.filter(
            status='pending'
        ).aggregate(
            total=models.Sum('amount_earned')
        )['total'] or Decimal('0.00')


class ReferralClick(models.Model):
    """
    Track clicks on referral links.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    affiliate = models.ForeignKey(
        AffiliateProfile,
        on_delete=models.CASCADE,
        related_name='referral_clicks'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referrer_url = models.URLField(blank=True)
    landing_page = models.URLField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Referral Click'
        verbose_name_plural = 'Referral Clicks'
        indexes = [
            models.Index(fields=['affiliate', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"Click for {self.affiliate.referral_code} at {self.timestamp}"


class ReferralConversion(models.Model):
    """
    Track successful conversions (user registrations) from referrals.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    affiliate = models.ForeignKey(
        AffiliateProfile,
        on_delete=models.CASCADE,
        related_name='conversions'
    )
    referred_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='referral_source'
    )
    referral_click = models.ForeignKey(
        ReferralClick,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversion'
    )
    conversion_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Initial value of the conversion"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Referral Conversion'
        verbose_name_plural = 'Referral Conversions'
        indexes = [
            models.Index(fields=['affiliate', 'timestamp']),
            models.Index(fields=['referred_user']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"Conversion: {self.referred_user.email} → {self.affiliate.referral_code}"


class CommissionLedger(models.Model):
    """
    Track commission earnings for affiliates.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    affiliate = models.ForeignKey(
        AffiliateProfile,
        on_delete=models.CASCADE,
        related_name='commission_ledger'
    )
    referred_user_subscription = models.ForeignKey(
        'project_core.UserSubscription',
        on_delete=models.CASCADE,
        related_name='commission_entries'
    )
    conversion = models.ForeignKey(
        ReferralConversion,
        on_delete=models.CASCADE,
        related_name='commission_entries'
    )
    
    # Commission Details
    subscription_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Original subscription amount"
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Commission rate applied"
    )
    amount_earned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Commission amount earned"
    )
    
    # Period Tracking
    month_year = models.CharField(
        max_length=7,
        help_text="Format: YYYY-MM"
    )
    billing_period_start = models.DateTimeField()
    billing_period_end = models.DateTimeField()
    
    # Status Tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Payout Information
    paid_at = models.DateTimeField(null=True, blank=True)
    payout_method = models.CharField(max_length=20, blank=True)
    payout_transaction_id = models.CharField(max_length=100, blank=True)
    payout_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Commission Ledger Entry'
        verbose_name_plural = 'Commission Ledger Entries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['affiliate', 'month_year']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['month_year']),
        ]

    def __str__(self):
        return f"Commission: {self.affiliate.referral_code} - ${self.amount_earned} ({self.month_year})"

    def mark_as_paid(self, payout_method, transaction_id, fee=None):
        """Mark commission as paid."""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.payout_method = payout_method
        self.payout_transaction_id = transaction_id
        if fee:
            self.payout_fee = fee
        self.save()

    @property
    def net_amount(self):
        """Get net amount after fees."""
        return self.amount_earned - self.payout_fee


class AffiliateResource(models.Model):
    """
    Resources available to affiliates (banners, templates, etc.).
    """
    RESOURCE_TYPES = [
        ('banner', 'Banner'),
        ('email_template', 'Email Template'),
        ('social_template', 'Social Media Template'),
        ('landing_page', 'Landing Page'),
        ('tutorial', 'Tutorial'),
        ('video', 'Video'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    file_url = models.URLField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    download_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Affiliate Resource'
        verbose_name_plural = 'Affiliate Resources'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.resource_type})"

    def increment_download_count(self):
        """Increment download count."""
        self.download_count += 1
        self.save(update_fields=['download_count'])