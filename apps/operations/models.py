from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, DecimalValidator
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class ManagedLocation(models.Model):
    """
    Model representing a user's actual placed vending machine location.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='managed_locations'
    )
    location_name = models.CharField(
        max_length=200,
        help_text="Name of the business/location"
    )
    address_details = models.TextField(
        help_text="Full address including street, city, state, zip"
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary contact person at location"
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number"
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="Contact email address"
    )
    image = models.ImageField(
        upload_to='managed_locations/',
        blank=True,
        null=True,
        help_text="Photo of the location"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the location"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this location is currently active"
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Longitude coordinate"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Managed Location'
        verbose_name_plural = 'Managed Locations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['location_name']),
        ]

    def __str__(self):
        return f"{self.location_name} - {self.user.email}"

    @property
    def total_machines(self):
        """Get total number of machines at this location."""
        return self.placed_machines.filter(is_active=True).count()

    @property
    def total_revenue_this_month(self):
        """Calculate total revenue for current month."""
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return CollectionData.objects.filter(
            visit_log__placed_machine__managed_location=self,
            visit_log__visit_date__gte=current_month
        ).aggregate(
            total=models.Sum('cash_collected')
        )['total'] or Decimal('0.00')

    @property
    def coordinates(self):
        """Return coordinates as a formatted string."""
        if self.latitude and self.longitude:
            return f"{self.latitude},{self.longitude}"
        return None


class PlacedMachine(models.Model):
    """
    Model representing a vending machine placed at a managed location.
    """
    MACHINE_TYPE_CHOICES = [
        ('snack', 'Snack Machine'),
        ('drink', 'Drink Machine'),
        ('claw', 'Claw Machine'),
        ('hot_food', 'Hot Food Kiosk'),
        ('ice_cream', 'Ice Cream Machine'),
        ('coffee', 'Coffee Machine'),
        ('combo', 'Combo Machine'),
        ('arcade', 'Arcade Game'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    managed_location = models.ForeignKey(
        ManagedLocation,
        on_delete=models.CASCADE,
        related_name='placed_machines'
    )
    machine_type = models.CharField(
        max_length=20,
        choices=MACHINE_TYPE_CHOICES,
        help_text="Type of vending machine"
    )
    machine_identifier = models.CharField(
        max_length=100,
        blank=True,
        help_text="Serial number or custom identifier"
    )
    date_placed = models.DateField(
        help_text="Date when machine was placed"
    )
    commission_percentage_to_location = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Percentage of revenue paid to location (0-100%)"
    )
    vend_price_range = models.CharField(
        max_length=50,
        help_text="Price range of items (e.g., '$1.00-$2.50')"
    )
    cost_per_vend = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Average cost per vend/play"
    )
    image = models.ImageField(
        upload_to='placed_machines/',
        blank=True,
        null=True,
        help_text="Photo of the machine"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this machine is currently active"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the machine"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Placed Machine'
        verbose_name_plural = 'Placed Machines'
        ordering = ['-date_placed']
        indexes = [
            models.Index(fields=['managed_location', 'is_active']),
            models.Index(fields=['machine_type']),
            models.Index(fields=['date_placed']),
        ]

    def __str__(self):
        return f"{self.get_machine_type_display()} at {self.managed_location.location_name}"

    @property
    def total_collections_this_month(self):
        """Calculate total collections for current month."""
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return CollectionData.objects.filter(
            visit_log__placed_machine=self,
            visit_log__visit_date__gte=current_month
        ).aggregate(
            total=models.Sum('cash_collected')
        )['total'] or Decimal('0.00')

    @property
    def average_per_visit(self):
        """Calculate average collection per visit."""
        total_collections = CollectionData.objects.filter(
            visit_log__placed_machine=self
        ).aggregate(
            total=models.Sum('cash_collected'),
            count=models.Count('id')
        )
        
        if total_collections['count'] and total_collections['total']:
            return total_collections['total'] / total_collections['count']
        return Decimal('0.00')

    @property
    def days_since_placement(self):
        """Calculate days since machine was placed."""
        return (timezone.now().date() - self.date_placed).days


class VisitLog(models.Model):
    """
    Model representing a visit to a placed machine for collection/maintenance.
    """
    VISIT_TYPE_CHOICES = [
        ('collection', 'Collection'),
        ('maintenance', 'Maintenance'),
        ('restock', 'Restock'),
        ('inspection', 'Inspection'),
        ('removal', 'Removal'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    placed_machine = models.ForeignKey(
        PlacedMachine,
        on_delete=models.CASCADE,
        related_name='visit_logs'
    )
    visit_date = models.DateTimeField(
        help_text="Date and time of visit"
    )
    visit_type = models.CharField(
        max_length=20,
        choices=VISIT_TYPE_CHOICES,
        default='collection',
        help_text="Type of visit"
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes about the visit"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Visit Log'
        verbose_name_plural = 'Visit Logs'
        ordering = ['-visit_date']
        indexes = [
            models.Index(fields=['placed_machine', 'visit_date']),
            models.Index(fields=['visit_type']),
            models.Index(fields=['visit_date']),
        ]

    def __str__(self):
        return f"{self.get_visit_type_display()} - {self.placed_machine} on {self.visit_date.date()}"

    @property
    def total_collected(self):
        """Get total cash collected during this visit."""
        collection_data = getattr(self, 'collection_data', None)
        return collection_data.cash_collected if collection_data else Decimal('0.00')


class CollectionData(models.Model):
    """
    Model representing financial data collected during a visit.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit_log = models.OneToOneField(
        VisitLog,
        on_delete=models.CASCADE,
        related_name='collection_data'
    )
    cash_collected = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount of cash collected"
    )
    items_sold_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Estimated value of items sold (optional)"
    )
    commission_paid_to_location = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Commission paid to location owner"
    )
    restock_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost of restocking items"
    )
    maintenance_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost of maintenance during visit"
    )
    restock_notes = models.TextField(
        blank=True,
        help_text="Notes about restocking"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Collection Data'
        verbose_name_plural = 'Collection Data'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visit_log']),
            models.Index(fields=['cash_collected']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Collection: ${self.cash_collected} - {self.visit_log.placed_machine}"

    @property
    def net_profit(self):
        """Calculate net profit from this collection."""
        return self.cash_collected - self.commission_paid_to_location - self.restock_cost - self.maintenance_cost

    @property
    def profit_margin(self):
        """Calculate profit margin percentage."""
        if self.cash_collected > 0:
            return (self.net_profit / self.cash_collected) * 100
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        """Auto-calculate commission if not provided."""
        if not self.commission_paid_to_location:
            commission_rate = self.visit_log.placed_machine.commission_percentage_to_location / 100
            self.commission_paid_to_location = self.cash_collected * commission_rate
        super().save(*args, **kwargs)