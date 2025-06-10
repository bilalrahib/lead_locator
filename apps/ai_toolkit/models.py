from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class GeneratedScript(models.Model):
    """
    Model to store AI-generated sales scripts.
    """
    SCRIPT_TYPE_CHOICES = [
        ('cold_call', 'Cold Call Script'),
        ('email', 'Email Template'),
        ('in_person', 'In-Person Script'),
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
        related_name='generated_scripts'
    )
    script_type = models.CharField(max_length=20, choices=SCRIPT_TYPE_CHOICES)
    target_location_name = models.CharField(
        max_length=255,
        help_text="Name of the target business/location"
    )
    target_location_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Category of the target location (e.g., Restaurant, Office)"
    )
    target_machine_type = models.CharField(
        max_length=30,
        choices=MACHINE_TYPE_CHOICES,
        help_text="Type of vending machine for this location"
    )
    script_content = models.TextField(help_text="The generated script content")
    is_template = models.BooleanField(
        default=False,
        help_text="Whether this is a pre-made template"
    )
    regeneration_count = models.IntegerField(
        default=0,
        help_text="Number of times this script has been regenerated"
    )
    ai_model_used = models.CharField(
        max_length=50,
        blank=True,
        help_text="AI model used to generate this script"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Generated Script'
        verbose_name_plural = 'Generated Scripts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'script_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_template']),
        ]

    def __str__(self):
        return f"{self.get_script_type_display()} for {self.target_location_name}"

    @property
    def can_regenerate(self):
        """Check if user can regenerate this script based on subscription."""
        if not hasattr(self.user, 'subscription') or not self.user.subscription:
            return False
        
        subscription = self.user.subscription
        if not subscription.is_active:
            return False
            
        # Free plan cannot regenerate
        if subscription.plan.name == 'FREE':
            return False
            
        return subscription.plan.regeneration_allowed


class JarvisConversation(models.Model):
    """
    Model to store JARVIS AI assistant conversations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='jarvis_conversations'
    )
    session_id = models.CharField(
        max_length=100,
        help_text="Session identifier for grouping related messages"
    )
    user_message = models.TextField(help_text="User's input message")
    jarvis_response = models.TextField(help_text="JARVIS AI response")
    conversation_type = models.CharField(
        max_length=50,
        choices=[
            ('general', 'General Chat'),
            ('script_generation', 'Script Generation'),
            ('business_advice', 'Business Advice'),
            ('logo_generation', 'Logo Generation'),
            ('social_media', 'Social Media Content'),
        ],
        default='general'
    )
    ai_model_used = models.CharField(max_length=50, blank=True)
    response_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Response time in milliseconds"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'JARVIS Conversation'
        verbose_name_plural = 'JARVIS Conversations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'session_id']),
            models.Index(fields=['conversation_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"JARVIS chat with {self.user.email} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class BusinessCalculation(models.Model):
    """
    Model to store business calculation results.
    """
    CALCULATION_TYPE_CHOICES = [
        ('lead_value_estimator', 'Lead Value Estimator'),
        ('snack_price_calculator', 'Snack Price Calculator'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='business_calculations'
    )
    calculation_type = models.CharField(max_length=30, choices=CALCULATION_TYPE_CHOICES)
    input_parameters = models.JSONField(
        help_text="Input parameters used for the calculation"
    )
    calculation_results = models.JSONField(
        help_text="Results of the calculation"
    )
    notes = models.TextField(
        blank=True,
        help_text="User notes about this calculation"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Business Calculation'
        verbose_name_plural = 'Business Calculations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'calculation_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_calculation_type_display()} - {self.user.email}"


class ScriptTemplate(models.Model):
    """
    Model for pre-made script templates.
    """
    SCRIPT_TYPE_CHOICES = GeneratedScript.SCRIPT_TYPE_CHOICES
    MACHINE_TYPE_CHOICES = GeneratedScript.MACHINE_TYPE_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Template name")
    script_type = models.CharField(max_length=20, choices=SCRIPT_TYPE_CHOICES)
    machine_type = models.CharField(
        max_length=30,
        choices=MACHINE_TYPE_CHOICES,
        blank=True,
        help_text="Specific machine type, or blank for general use"
    )
    location_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Target location category"
    )
    content = models.TextField(help_text="Template content with placeholders")
    is_premium = models.BooleanField(
        default=False,
        help_text="Whether this template requires a paid subscription"
    )
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this template has been used"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Script Template'
        verbose_name_plural = 'Script Templates'
        ordering = ['script_type', 'name']
        indexes = [
            models.Index(fields=['script_type', 'is_active']),
            models.Index(fields=['is_premium']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_script_type_display()})"

    def can_access(self, user):
        """Check if user can access this template based on subscription."""
        if not self.is_premium:
            return True
            
        if not hasattr(user, 'subscription') or not user.subscription:
            return False
            
        subscription = user.subscription
        return subscription.is_active and subscription.plan.name != 'FREE'