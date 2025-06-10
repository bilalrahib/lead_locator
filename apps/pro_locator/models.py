from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
# from apps.locator.models import SearchHistory, LocationData
import uuid

# Check if these models exist, if not we'll create references
try:
    from apps.locator.models import SearchHistory, LocationData
except ImportError:
    # If locator models don't exist yet, we'll handle this in migration dependencies
    pass


# Add the machine type choices that should match your locator app
MACHINE_TYPE_CHOICES = [
    ('snack', 'Snack Machine'),
    ('drink', 'Drink Machine'), 
    ('claw', 'Claw Machine'),
    ('combo', 'Combo Machine'),
    ('hot_food', 'Hot Food Kiosk'),
    ('ice_cream', 'Ice Cream Machine'),
    ('coffee', 'Coffee Machine'),
]

User = get_user_model()


class ClientProfile(models.Model):
    """
    Model for client profiles managed by Elite/Professional users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='client_profiles',
        help_text="Elite/Professional user who owns this client"
    )
    client_name = models.CharField(max_length=255, help_text="Client business name")
    client_contact_name = models.CharField(max_length=255, blank=True, help_text="Primary contact name")
    client_email = models.EmailField(blank=True, help_text="Client email address")
    client_phone = models.CharField(max_length=20, blank=True, help_text="Client phone number")
    client_zip_code = models.CharField(max_length=10, help_text="Client's primary ZIP code")
    client_city = models.CharField(max_length=100, blank=True, help_text="Client's city")
    client_state = models.CharField(max_length=50, blank=True, help_text="Client's state")
    default_machine_type = models.CharField(
        max_length=30,
        choices=MACHINE_TYPE_CHOICES,
        help_text="Default machine type for this client"
    )
    client_notes = models.TextField(blank=True, help_text="Additional notes about the client")
    is_active = models.BooleanField(default=True, help_text="Whether this client is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Client Profile'
        verbose_name_plural = 'Client Profiles'
        ordering = ['client_name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['client_zip_code']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.client_name} ({self.user.email})"

    @property
    def total_searches(self):
        """Get total number of searches for this client."""
        return self.saved_searches.count()

    @property
    def total_locations_found(self):
        """Get total number of locations found for this client."""
        return ClientLocationData.objects.filter(client_profile=self).count()



class ClientSavedSearch(models.Model):
    """
    Model for searches saved for specific clients.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_profile = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name='saved_searches'
    )
    search_history = models.ForeignKey(
        SearchHistory,
        on_delete=models.CASCADE,
        related_name='client_searches',
        help_text="Reference to the original search"
    )
    search_name = models.CharField(max_length=255, help_text="Custom name for this search")
    notes = models.TextField(blank=True, help_text="Notes about this search for the client")
    is_shared_with_client = models.BooleanField(
        default=False,
        help_text="Whether this search has been shared with the client"
    )
    shared_at = models.DateTimeField(null=True, blank=True, help_text="When this search was shared")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Client Saved Search'
        verbose_name_plural = 'Client Saved Searches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client_profile', 'created_at']),
            models.Index(fields=['is_shared_with_client']),
        ]

    def __str__(self):
        return f"{self.search_name} - {self.client_profile.client_name}"

    def mark_shared(self):
        """Mark this search as shared with the client."""
        self.is_shared_with_client = True
        self.shared_at = timezone.now()
        self.save(update_fields=['is_shared_with_client', 'shared_at'])


class ClientLocationData(models.Model):
    """
    Many-to-many relationship between clients and location data.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_profile = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name='client_locations'
    )
    location_data = models.ForeignKey(
        LocationData,
        on_delete=models.CASCADE,
        related_name='client_assignments'
    )
    saved_search = models.ForeignKey(
        ClientSavedSearch,
        on_delete=models.CASCADE,
        related_name='assigned_locations'
    )
    notes = models.TextField(blank=True, help_text="Client-specific notes for this location")
    priority = models.IntegerField(
        default=0,
        help_text="Priority ranking for this client (higher = more priority)"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New Lead'),
            ('contacted', 'Contacted'),
            ('interested', 'Interested'),
            ('not_interested', 'Not Interested'),
            ('placed', 'Machine Placed'),
            ('rejected', 'Rejected'),
        ],
        default='new'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Client Location Data'
        verbose_name_plural = 'Client Location Data'
        unique_together = ['client_profile', 'location_data', 'saved_search']
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['client_profile', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"{self.location_data.name} - {self.client_profile.client_name}"


class WhiteLabelSettings(models.Model):
    """
    Model for white-label branding settings for Professional users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='whitelabel_settings'
    )
    company_name = models.CharField(max_length=255, help_text="Custom company name for branding")
    company_logo = models.ImageField(
        upload_to='whitelabel/logos/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg', 'svg'])],
        help_text="Company logo for exports and client portal"
    )
    primary_color = models.CharField(
        max_length=7,
        default='#fb6d00',
        help_text="Primary brand color (hex format)"
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#ffffff',
        help_text="Secondary brand color (hex format)"
    )
    company_website = models.URLField(blank=True, help_text="Company website URL")
    company_phone = models.CharField(max_length=20, blank=True, help_text="Company phone number")
    company_email = models.EmailField(blank=True, help_text="Company contact email")
    custom_domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom domain for client portal (e.g., clients.yourcompany.com)"
    )
    remove_vending_hive_branding = models.BooleanField(
        default=False,
        help_text="Remove Vending Hive branding from client-facing materials"
    )
    is_active = models.BooleanField(default=True, help_text="Whether white-labeling is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'White Label Settings'
        verbose_name_plural = 'White Label Settings'

    def __str__(self):
        return f"White Label Settings - {self.user.email}"

    @property
    def has_custom_branding(self):
        """Check if user has custom branding configured."""
        return bool(self.company_name and (self.company_logo or self.primary_color != '#fb6d00'))