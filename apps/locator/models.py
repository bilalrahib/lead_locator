from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class SearchHistory(models.Model):
    """
    Model to track user search history for vending machine locations.
    """
    RADIUS_CHOICES = [
        (5, '5 miles'),
        (10, '10 miles'),
        (15, '15 miles'),
        (20, '20 miles'),
        (25, '25 miles'),
        (30, '30 miles'),
        (40, '40 miles'),
    ]
    
    MACHINE_TYPE_CHOICES = [
        ('snack_machine', 'Snack Machine'),
        ('drink_machine', 'Drink Machine'),
        ('claw_machine', 'Claw Machine'),
        ('hot_food_kiosk', 'Hot Food Kiosk'),
        ('ice_cream_machine', 'Ice Cream Machine'),
        ('coffee_machine', 'Coffee Machine'),
        ('combo_machine', 'Combo Snack/Drink Machine'),
        ('healthy_snack_machine', 'Healthy Snack Machine'),
        ('fresh_food_machine', 'Fresh Food Machine'),
        ('toy_machine', 'Toy/Prize Machine'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='search_history'
    )
    zip_code = models.CharField(max_length=10, help_text="ZIP code for search center")
    radius = models.IntegerField(
        choices=RADIUS_CHOICES,
        default=10,
        help_text="Search radius in miles"
    )
    machine_type = models.CharField(
        max_length=30,
        choices=MACHINE_TYPE_CHOICES,
        help_text="Type of vending machine"
    )
    building_types_filter = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional filter for specific building types"
    )
    results_count = models.IntegerField(
        default=0,
        help_text="Number of results returned for this search"
    )
    search_parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional search parameters"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Search History'
        verbose_name_plural = 'Search Histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['zip_code', 'created_at']),
            models.Index(fields=['machine_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.zip_code} ({self.machine_type}) - {self.created_at.strftime('%Y-%m-%d')}"

    @property
    def search_summary(self):
        """Get human-readable search summary."""
        return (
            f"{self.get_machine_type_display()} within {self.radius} miles of {self.zip_code}"
        )


class LocationData(models.Model):
    """
    Model to store discovered vending machine location data.
    """
    FOOT_TRAFFIC_CHOICES = [
        ('very_low', 'Very Low'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('very_high', 'Very High'),
    ]
    
    BUSINESS_STATUS_CHOICES = [
        ('operational', 'Operational'),
        ('closed_temporarily', 'Closed Temporarily'),
        ('closed_permanently', 'Closed Permanently'),
        ('unknown', 'Unknown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search_history = models.ForeignKey(
        SearchHistory,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    name = models.CharField(max_length=255, help_text="Business name")
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="OSM-derived category"
    )
    detailed_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Google Places derived category"
    )
    address = models.TextField(help_text="Full address")
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Longitude coordinate"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Business phone number"
    )
    email = models.EmailField(
        blank=True,
        help_text="Business email address"
    )
    website = models.URLField(
        blank=True,
        help_text="Business website"
    )
    business_hours_text = models.TextField(
        blank=True,
        help_text="Business hours in text format"
    )
    google_place_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Google Places API place ID"
    )
    google_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Google rating (0-5)"
    )
    google_user_ratings_total = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total number of Google reviews"
    )
    google_business_status = models.CharField(
        max_length=30,
        choices=BUSINESS_STATUS_CHOICES,
        default='unknown',
        help_text="Business operational status"
    )
    maps_url = models.URLField(
        blank=True,
        help_text="Google Maps URL"
    )
    foot_traffic_estimate = models.CharField(
        max_length=20,
        choices=FOOT_TRAFFIC_CHOICES,
        default='moderate',
        help_text="Estimated foot traffic level"
    )
    google_popular_times_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Popular times data from Google"
    )
    osm_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw OpenStreetMap data"
    )
    google_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw Google Places data"
    )
    priority_score = models.IntegerField(
        default=0,
        help_text="Priority score for lead ranking"
    )
    contact_completeness = models.CharField(
        max_length=20,
        choices=[
            ('both', 'Phone & Email'),
            ('phone_only', 'Phone Only'),
            ('email_only', 'Email Only'),
            ('none', 'No Contact Info'),
        ],
        default='none'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Location Data'
        verbose_name_plural = 'Location Data'
        ordering = ['-priority_score', 'name']
        indexes = [
            models.Index(fields=['search_history', 'priority_score']),
            models.Index(fields=['google_place_id']),
            models.Index(fields=['contact_completeness']),
            models.Index(fields=['foot_traffic_estimate']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.name} - {self.address}"

    @property
    def coordinates(self):
        """Get coordinates as tuple."""
        return (float(self.latitude), float(self.longitude))

    @property
    def has_contact_info(self):
        """Check if location has any contact information."""
        return bool(self.phone or self.email)

    @property
    def contact_score(self):
        """Calculate contact completeness score."""
        if self.phone and self.email:
            return 3
        elif self.phone or self.email:
            return 2
        else:
            return 1

    def calculate_priority_score(self):
        """Calculate and update priority score based on various factors."""
        score = 0
        
        # Contact information scoring (highest priority)
        if self.phone and self.email:
            score += 50
            self.contact_completeness = 'both'
        elif self.phone:
            score += 30
            self.contact_completeness = 'phone_only'
        elif self.email:
            score += 20
            self.contact_completeness = 'email_only'
        else:
            score += 0
            self.contact_completeness = 'none'
        
        # Google rating scoring
        if self.google_rating:
            score += int(self.google_rating * 5)  # 0-25 points
        
        # Review count scoring
        if self.google_user_ratings_total:
            if self.google_user_ratings_total >= 100:
                score += 15
            elif self.google_user_ratings_total >= 50:
                score += 10
            elif self.google_user_ratings_total >= 10:
                score += 5
        
        # Foot traffic scoring
        traffic_scores = {
            'very_high': 15,
            'high': 10,
            'moderate': 5,
            'low': 2,
            'very_low': 0
        }
        score += traffic_scores.get(self.foot_traffic_estimate, 0)
        
        # Business status scoring
        if self.google_business_status == 'operational':
            score += 10
        elif self.google_business_status in ['closed_temporarily', 'unknown']:
            score += 5
        
        self.priority_score = score
        return score


class UserLocationPreference(models.Model):
    """
    Model to store user preferences for location searches.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='location_preferences'
    )
    preferred_machine_types = models.JSONField(
        default=list,
        help_text="User's preferred machine types"
    )
    preferred_radius = models.IntegerField(
        choices=SearchHistory.RADIUS_CHOICES,
        default=10,
        help_text="Default search radius"
    )
    preferred_building_types = models.JSONField(
        default=list,
        help_text="Preferred building types for searches"
    )
    excluded_categories = models.JSONField(
        default=list,
        help_text="Categories to exclude from searches"
    )
    minimum_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Minimum Google rating filter"
    )
    require_contact_info = models.BooleanField(
        default=True,
        help_text="Only show locations with contact information"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Location Preference'
        verbose_name_plural = 'User Location Preferences'

    def __str__(self):
        return f"{self.user.email} - Location Preferences"


class ExcludedLocation(models.Model):
    """
    Model to track locations that users want to exclude from future searches.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='excluded_locations'
    )
    google_place_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Google Places ID of excluded location"
    )
    location_name = models.CharField(
        max_length=255,
        help_text="Name of the excluded location"
    )
    reason = models.CharField(
        max_length=50,
        choices=[
            ('already_contacted', 'Already Contacted'),
            ('not_interested', 'Not Interested'),
            ('poor_location', 'Poor Location'),
            ('closed', 'Business Closed'),
            ('other', 'Other'),
        ],
        default='other'
    )
    notes = models.TextField(blank=True, help_text="Additional notes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Excluded Location'
        verbose_name_plural = 'Excluded Locations'
        unique_together = ['user', 'google_place_id']
        indexes = [
            models.Index(fields=['user', 'google_place_id']),
        ]

    def __str__(self):
        return f"{self.user.email} - Excluded: {self.location_name}"