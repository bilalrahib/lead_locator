from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator
from django.utils import timezone
from django.urls import reverse
import uuid

User = get_user_model


class SupportTicket(models.Model):
    """
    Model for basic support ticket system.
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open'
    )
    admin_notes = models.TextField(blank=True, help_text="Internal notes for admin")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Ticket #{self.id.hex[:8]}: {self.subject}"

    def save(self, *args, **kwargs):
        if self.status in ['resolved', 'closed'] and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status not in ['resolved', 'closed'] and self.resolved_at:
            self.resolved_at = None
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.status in ['open', 'in_progress']

    def get_absolute_url(self):
        return reverse('project_core:support_ticket_detail', kwargs={'pk': self.pk})


class WeatherLocation(models.Model):
    """
    Model to store user's weather location preferences.
    """
    user = models.OneToOneField(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='weather_location'
    )
    address = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=10)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Weather Location'
        verbose_name_plural = 'Weather Locations'

    def __str__(self):
        return f"{self.user.username} - {self.address}"

    @property
    def coordinates(self):
        if self.latitude and self.longitude:
            return f"{self.latitude},{self.longitude}"
        return None


class SystemNotification(models.Model):
    """
    Model for system-wide notifications.
    """
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
        ('maintenance', 'Maintenance'),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='info'
    )
    is_active = models.BooleanField(default=True)
    show_on_homepage = models.BooleanField(default=False)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'System Notification'
        verbose_name_plural = 'System Notifications'

    def __str__(self):
        return self.title

    @property
    def is_current(self):
        """Check if notification is currently active."""
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True


class ContactMessage(models.Model):
    """
    Model for contact form submissions from public homepage.
    """
    name = models.CharField(max_length=100)
    email = models.EmailField(validators=[EmailValidator()])
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f"Contact from {self.name}: {self.subject}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])


class SubscriptionPlan(models.Model):
    """
    Model for subscription plans - moved here from subscriptions app for circular import issues.
    """
    PLAN_CHOICES = [
        ('FREE', 'Free'),
        ('STARTER', 'Starter'),
        ('PRO', 'Pro'),
        ('ELITE', 'Elite'),
        ('PROFESSIONAL', 'Professional'),
    ]

    name = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    leads_per_month = models.IntegerField()
    leads_per_search_range = models.CharField(max_length=20, help_text="e.g., '10-15'")
    script_templates_count = models.IntegerField()
    regeneration_allowed = models.BooleanField(default=False)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return f"{self.get_name_display()} - ${self.price}/month"

    @property
    def is_free(self):
        return self.name == 'FREE'

    @property
    def is_premium(self):
        return self.name in ['ELITE', 'PROFESSIONAL']



class UserSubscription(models.Model):
    """
    Model for user subscriptions - moved here from subscriptions app for circular import issues.
    """
    user = models.OneToOneField(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    searches_used_this_period = models.IntegerField(default=0)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Subscription'
        verbose_name_plural = 'User Subscriptions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['plan', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"

    @property
    def is_expired(self):
        if not self.end_date:
            return False
        from django.utils import timezone
        return timezone.now() > self.end_date

    def can_search(self):
        return self.is_active and not self.is_expired and self.searches_used_this_period < self.plan.leads_per_month

    def use_search(self):
        if self.can_search():
            self.searches_used_this_period += 1
            self.save(update_fields=['searches_used_this_period'])
            return True
        return False

    def searches_left_this_period(self):
        return max(0, self.plan.leads_per_month - self.searches_used_this_period)