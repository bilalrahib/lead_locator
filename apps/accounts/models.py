# import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.urls import reverse
from datetime import timedelta
import uuid

class CustomUser(AbstractUser):
    """
    Custom User model for Vending Hive with enhanced security and profile features.
    """
    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, help_text="Email address (used for login)")
    
    # Phone validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True,
        help_text="Phone number"
    )
    is_approved_affiliate = models.BooleanField(
        default=False,
        help_text="Designates whether this user is an approved affiliate"
    )
    # Security fields
    failed_login_attempts = models.IntegerField(
        default=0, 
        help_text="Number of consecutive failed login attempts"
    )
    is_locked = models.BooleanField(
        default=False, 
        help_text="Account locked due to failed login attempts"
    )
    lock_expires_at = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="When account lock expires"
    )
    last_login_ip = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        help_text="IP address of last login"
    )
    
    # Email verification
    email_verified = models.BooleanField(
        default=False, 
        help_text="Email address has been verified"
    )
    email_verification_token = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Token for email verification"
    )
    email_verification_sent_at = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="When verification email was sent"
    )
    
    # Password reset
    password_reset_token = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Token for password reset"
    )
    password_reset_expires_at = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="When password reset token expires"
    )
    
    # Profile fields
    avatar = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True, 
        help_text="Profile picture"
    )
    bio = models.TextField(
        max_length=500, 
        blank=True, 
        help_text="Short bio or description"
    )
    company_name = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Company or business name"
    )
    website = models.URLField(
        blank=True, 
        help_text="Personal or company website"
    )
    
    # Subscription reference (will be used by subscriptions app)
    current_subscription = models.ForeignKey(
        'project_core.UserSubscription',  # Updated reference
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscribed_user',
        help_text="Current active subscription"
    )
    
    # Preferences
    email_notifications = models.BooleanField(
        default=True, 
        help_text="Receive email notifications"
    )
    marketing_emails = models.BooleanField(
        default=False, 
        help_text="Receive marketing emails"
    )
    timezone_preference = models.CharField(
        max_length=50, 
        default='UTC', 
        help_text="User's preferred timezone"
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Last user activity timestamp"
    )
    
    # Make email the primary login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['created_at']),
            models.Index(fields=['email_verification_token']),
            models.Index(fields=['password_reset_token']),
            models.Index(fields=['is_locked', 'lock_expires_at']),
        ]

    def __str__(self):
        return f"{self.email} ({self.full_name})"

    @property
    def full_name(self):
        """Return the user's full name."""
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username

    @property
    def is_account_locked(self):
        """Check if account is currently locked."""
        if not self.is_locked:
            return False
        
        if self.lock_expires_at and timezone.now() > self.lock_expires_at:
            # Lock has expired, unlock the account
            self.unlock_account()
            return False
        
        return True

    @property
    def subscription_status(self):
        """Get current subscription status."""
        if self.current_subscription and self.current_subscription.is_active:
            return self.current_subscription.plan.name
        return 'FREE'

    @property
    def is_premium_user(self):
        """Check if user has premium subscription."""
        return self.subscription_status in ['ELITE', 'PROFESSIONAL']

    def lock_account(self, duration_minutes=5):
        """
        Lock the account for a specified duration.
        
        Args:
            duration_minutes: How long to lock the account
        """
        self.is_locked = True
        self.lock_expires_at = timezone.now() + timedelta(minutes=duration_minutes)
        self.save(update_fields=['is_locked', 'lock_expires_at'])

    def unlock_account(self):
        """Unlock the account and reset failed attempts."""
        self.is_locked = False
        self.failed_login_attempts = 0
        self.lock_expires_at = None
        self.save(update_fields=['is_locked', 'failed_login_attempts', 'lock_expires_at'])

    def increment_failed_attempts(self, max_attempts=5):
        """
        Increment failed login attempts and lock if necessary.
        
        Args:
            max_attempts: Maximum attempts before locking
        """
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= max_attempts:
            self.lock_account()
        else:
            self.save(update_fields=['failed_login_attempts'])

    def reset_failed_attempts(self):
        """Reset failed login attempts on successful login."""
        if self.failed_login_attempts > 0:
            self.failed_login_attempts = 0
            self.save(update_fields=['failed_login_attempts'])

    def generate_email_verification_token(self):
        """Generate and save email verification token."""
        from django.utils.crypto import get_random_string
        
        self.email_verification_token = get_random_string(64)
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        return self.email_verification_token

    def verify_email(self, token):
        """
        Verify email with token.
        
        Args:
            token: Verification token
            
        Returns:
            bool: True if verification successful
        """
        if (self.email_verification_token == token and 
            self.email_verification_sent_at and 
            timezone.now() - self.email_verification_sent_at < timedelta(days=7)):
            
            self.email_verified = True
            self.email_verification_token = ''
            self.email_verification_sent_at = None
            self.save(update_fields=[
                'email_verified', 
                'email_verification_token', 
                'email_verification_sent_at'
            ])
            return True
        return False

    def generate_password_reset_token(self):
        """Generate and save password reset token."""
        from django.utils.crypto import get_random_string
        
        self.password_reset_token = get_random_string(64)
        self.password_reset_expires_at = timezone.now() + timedelta(hours=24)
        self.save(update_fields=['password_reset_token', 'password_reset_expires_at'])
        return self.password_reset_token

    def verify_password_reset_token(self, token):
        """
        Verify password reset token.
        
        Args:
            token: Reset token
            
        Returns:
            bool: True if token is valid
        """
        return (self.password_reset_token == token and 
                self.password_reset_expires_at and 
                timezone.now() < self.password_reset_expires_at)

    def clear_password_reset_token(self):
        """Clear password reset token after use."""
        self.password_reset_token = ''
        self.password_reset_expires_at = None
        self.save(update_fields=['password_reset_token', 'password_reset_expires_at'])

    def update_last_activity(self, ip_address=None):
        """Update last activity timestamp and IP."""
        self.last_activity = timezone.now()
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['last_activity', 'last_login_ip'])

    def get_absolute_url(self):
        """Get user profile URL."""
        return reverse('accounts:profile_detail', kwargs={'pk': self.pk})

    def can_receive_email(self, email_type='notification'):
        """
        Check if user can receive emails of specified type.
        
        Args:
            email_type: 'notification' or 'marketing'
            
        Returns:
            bool: True if user can receive emails
        """
        if not self.email_verified:
            return False
        
        if email_type == 'marketing':
            return self.marketing_emails
        
        return self.email_notifications

    def get_subscription_limits(self):
        """Get user's subscription limits."""
        if self.current_subscription and self.current_subscription.is_active:
            plan = self.current_subscription.plan
            return {
                'searches_per_month': plan.leads_per_month,
                'script_templates': plan.script_templates_count,
                'regeneration_allowed': plan.regeneration_allowed,
                'plan_name': plan.name
            }
        
        # Default free plan limits
        return {
            'searches_per_month': 3,
            'script_templates': 1,
            'regeneration_allowed': False,
            'plan_name': 'FREE'
        }


class UserProfile(models.Model):
    """
    Extended user profile with additional business information.
    """
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    
    # Business information
    business_type = models.CharField(
        max_length=50,
        choices=[
            ('individual', 'Individual Operator'),
            ('small_business', 'Small Business'),
            ('large_business', 'Large Business'),
            ('consultant', 'Consultant/Agency'),
            ('other', 'Other')
        ],
        default='individual',
        help_text="Type of business"
    )
    years_in_business = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Years in vending business"
    )
    number_of_machines = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Current number of machines"
    )
    target_locations = models.TextField(
        blank=True, 
        help_text="Types of locations you target"
    )
    
    # Address information
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=50, default='US')
    
    # Social media
    linkedin_url = models.URLField(blank=True, help_text="LinkedIn profile")
    twitter_url = models.URLField(blank=True, help_text="Twitter profile")
    facebook_url = models.URLField(blank=True, help_text="Facebook page")
    
    # Preferences
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('sms', 'SMS'),
        ],
        default='email'
    )
    
    # Tracking
    profile_completed = models.BooleanField(
        default=False, 
        help_text="Profile completion status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.email} Profile"

    @property
    def completion_percentage(self):
        """Calculate profile completion percentage."""
        fields = [
            'business_type', 'years_in_business', 'number_of_machines',
            'address_line1', 'city', 'state', 'zip_code',
            'user.phone', 'user.company_name'
        ]
        
        completed = 0
        for field in fields:
            if '.' in field:
                obj, attr = field.split('.')
                value = getattr(getattr(self, obj), attr) if hasattr(self, obj) else None
            else:
                value = getattr(self, field, None)
            
            if value:
                completed += 1
        
        return int((completed / len(fields)) * 100)

    @property
    def full_address(self):
        """Get formatted full address."""
        parts = [
            self.address_line1,
            self.address_line2,
            f"{self.city}, {self.state} {self.zip_code}".strip(),
            self.country if self.country != 'US' else ''
        ]
        return ', '.join([part for part in parts if part])

    def mark_completed(self):
        """Mark profile as completed."""
        self.profile_completed = True
        self.save(update_fields=['profile_completed'])


class UserActivity(models.Model):
    """
    Track user activities for analytics and security.
    """
    ACTIVITY_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('email_change', 'Email Change'),
        ('profile_update', 'Profile Update'),
        ('subscription_change', 'Subscription Change'),
        ('search_performed', 'Search Performed'),
        ('script_generated', 'Script Generated'),
        ('support_ticket', 'Support Ticket Created'),
    ]

    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='activities'
    )
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True, help_text="Activity description")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional activity data")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['activity_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_activity_type_display()}"

    @classmethod
    def log_activity(cls, user, activity_type, description='', request=None, metadata=None):
        """
        Log user activity.
        
        Args:
            user: User instance
            activity_type: Type of activity
            description: Activity description
            request: HTTP request object
            metadata: Additional data
        """
        from apps.project_core.utils.helpers import get_client_ip, parse_user_agent
        
        data = {
            'user': user,
            'activity_type': activity_type,
            'description': description,
            'metadata': metadata or {}
        }
        
        if request:
            data['ip_address'] = get_client_ip(request)
            data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(**data)