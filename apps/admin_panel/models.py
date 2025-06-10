from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class AdminLog(models.Model):
    """
    Model to track admin actions for audit purposes.
    """
    ACTION_TYPES = [
        ('user_activate', 'User Activated'),
        ('user_deactivate', 'User Deactivated'),
        ('subscription_change', 'Subscription Changed'),
        ('credit_grant', 'Credits Granted'),
        ('affiliate_approve', 'Affiliate Approved'),
        ('affiliate_reject', 'Affiliate Rejected'),
        ('content_create', 'Content Created'),
        ('content_update', 'Content Updated'),
        ('content_delete', 'Content Deleted'),
        ('system_setting', 'System Setting Changed'),
        ('bulk_operation', 'Bulk Operation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_actions'
    )
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_actions_received',
        help_text="User affected by the action"
    )
    description = models.TextField(help_text="Detailed description of the action")
    before_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="State before the action"
    )
    after_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="State after the action"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Admin Log'
        verbose_name_plural = 'Admin Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin_user', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['target_user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.admin_user.email} - {self.get_action_type_display()}"


class ContentTemplate(models.Model):
    """
    Model for managing affiliate marketing templates and content.
    """
    TEMPLATE_TYPES = [
        ('email', 'Email Template'),
        ('social_post', 'Social Media Post'),
        ('banner', 'Banner/Image'),
        ('tutorial', 'Tutorial Link'),
        ('landing_page', 'Landing Page'),
        ('video', 'Video Content'),
    ]

    CONTENT_STATUS = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Template name")
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    title = models.CharField(max_length=300, help_text="Template title/subject")
    content = models.TextField(help_text="Template content/body")
    preview_url = models.URLField(blank=True, help_text="Preview or demo URL")
    thumbnail = models.ImageField(
        upload_to='admin_panel/templates/',
        null=True,
        blank=True,
        help_text="Template thumbnail"
    )
    description = models.TextField(blank=True, help_text="Template description")
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated tags"
    )
    status = models.CharField(max_length=20, choices=CONTENT_STATUS, default='draft')
    is_featured = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Content Template'
        verbose_name_plural = 'Content Templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template_type', 'status']),
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    def increment_usage(self):
        """Increment usage count."""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])

    @property
    def tag_list(self):
        """Return tags as a list."""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []


class SystemSettings(models.Model):
    """
    Model for storing system-wide configuration settings.
    """
    SETTING_TYPES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]

    key = models.CharField(max_length=100, unique=True, help_text="Setting key")
    value = models.TextField(help_text="Setting value")
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string')
    description = models.TextField(help_text="Setting description")
    category = models.CharField(
        max_length=50,
        default='general',
        help_text="Setting category for grouping"
    )
    is_active = models.BooleanField(default=True)
    is_editable = models.BooleanField(
        default=True,
        help_text="Whether this setting can be edited via admin panel"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings'
    )

    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
        ordering = ['category', 'key']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['key']),
        ]

    def __str__(self):
        return f"{self.key} = {self.value}"

    def get_typed_value(self):
        """Return value converted to appropriate type."""
        if self.setting_type == 'integer':
            try:
                return int(self.value)
            except ValueError:
                return 0
        elif self.setting_type == 'float':
            try:
                return float(self.value)
            except ValueError:
                return 0.0
        elif self.setting_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.setting_type == 'json':
            import json
            try:
                return json.loads(self.value)
            except json.JSONDecodeError:
                return {}
        else:
            return self.value

    def set_typed_value(self, value):
        """Set value with automatic type conversion."""
        if self.setting_type == 'json':
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)


class AdminDashboardStats(models.Model):
    """
    Model for caching dashboard statistics to improve performance.
    """
    stat_date = models.DateField(unique=True)
    total_users = models.IntegerField(default=0)
    new_users_today = models.IntegerField(default=0)
    active_subscriptions = models.IntegerField(default=0)
    revenue_today = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    searches_today = models.IntegerField(default=0)
    support_tickets_open = models.IntegerField(default=0)
    cache_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dashboard Stats'
        verbose_name_plural = 'Dashboard Stats'
        ordering = ['-stat_date']

    def __str__(self):
        return f"Dashboard Stats for {self.stat_date}"