from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, UserProfile, UserActivity


class UserProfileInline(admin.StackedInline):
    """Inline admin for user profile."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Information'
    
    fieldsets = (
        ('Business Information', {
            'fields': ('business_type', 'years_in_business', 'number_of_machines', 'target_locations')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country')
        }),
        ('Social Media', {
            'fields': ('linkedin_url', 'twitter_url', 'facebook_url'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': ('preferred_contact_method', 'profile_completed')
        }),
    )


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Custom admin for CustomUser model."""
    
    inlines = [UserProfileInline]
    
    # Display fields
    list_display = [
        'email', 'username', 'full_name', 'subscription_status_display',
        'email_verified', 'is_active', 'is_locked', 'date_joined_display', 'last_login_display'
    ]
    
    list_filter = [
        'is_staff', 'is_superuser', 'is_active', 'email_verified', 'is_locked',
        'marketing_emails', 'email_notifications', 'date_joined', 'last_login'
    ]
    
    search_fields = [
        'email', 'username', 'first_name', 'last_name', 'company_name', 'phone'
    ]
    
    ordering = ['-date_joined']
    
    readonly_fields = [
        'id', 'date_joined', 'last_login', 'last_activity', 'failed_login_attempts',
        'lock_expires_at', 'email_verification_sent_at', 'password_reset_expires_at',
        'subscription_status_display', 'account_age', 'profile_completion_display'
    ]
    
    # Fieldsets for detailed view
    fieldsets = UserAdmin.fieldsets + (
        ('Extended Profile', {
            'fields': ('phone', 'company_name', 'website', 'bio', 'avatar')
        }),
        ('Email & Verification', {
            'fields': (
                'email_verified', 'email_verification_token', 'email_verification_sent_at'
            ),
            'classes': ('collapse',)
        }),
        ('Security & Account Status', {
            'fields': (
                'failed_login_attempts', 'is_locked', 'lock_expires_at',
                'last_login_ip', 'last_activity'
            )
        }),
        ('Password Reset', {
            'fields': ('password_reset_token', 'password_reset_expires_at'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': (
                'email_notifications', 'marketing_emails', 'timezone_preference'
            )
        }),
        ('Subscription', {
            'fields': ('current_subscription', 'subscription_status_display'),
        }),
        ('Metadata', {
            'fields': ('id', 'account_age', 'profile_completion_display'),
            'classes': ('collapse',)
        }),
    )
    
    # Add fieldsets for user creation
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
        ('Additional Information', {
            'classes': ('wide',),
            'fields': ('phone', 'company_name', 'email_notifications', 'marketing_emails'),
        }),
    )
    
    actions = [
        'verify_emails', 'send_verification_emails', 'unlock_accounts',
        'deactivate_users', 'activate_users', 'reset_failed_attempts'
    ]

    def subscription_status_display(self, obj):
        """Display subscription status with color coding."""
        status = obj.subscription_status
        colors = {
            'FREE': '#6c757d',
            'STARTER': '#17a2b8',
            'PRO': '#28a745',
            'ELITE': '#ffc107',
            'PROFESSIONAL': '#dc3545'
        }
        color = colors.get(status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    subscription_status_display.short_description = 'Subscription'

    def date_joined_display(self, obj):
        """Display formatted join date."""
        return obj.date_joined.strftime('%Y-%m-%d %H:%M')
    date_joined_display.short_description = 'Joined'
    date_joined_display.admin_order_field = 'date_joined'

    def last_login_display(self, obj):
        """Display formatted last login."""
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M')
        return 'Never'
    last_login_display.short_description = 'Last Login'
    last_login_display.admin_order_field = 'last_login'

    def account_age(self, obj):
        """Display account age in days."""
        age = (timezone.now() - obj.date_joined).days
        return f"{age} days"
    account_age.short_description = 'Account Age'

    def profile_completion_display(self, obj):
        """Display profile completion percentage."""
        try:
            completion = obj.profile.completion_percentage
            color = '#28a745' if completion >= 80 else '#ffc107' if completion >= 50 else '#dc3545'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}%</span>',
                color, completion
            )
        except:
            return format_html('<span style="color: #dc3545;">No Profile</span>')
    profile_completion_display.short_description = 'Profile Complete'

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'current_subscription', 'profile'
        ).prefetch_related('activities')

    # Admin actions
    def verify_emails(self, request, queryset):
        """Mark selected users' emails as verified."""
        updated = queryset.update(email_verified=True, email_verification_token='')
        self.message_user(request, f'{updated} users had their emails verified.')
    verify_emails.short_description = "Mark emails as verified"

    def send_verification_emails(self, request, queryset):
        """Send verification emails to selected users."""
        from .services import UserEmailService
        email_service = UserEmailService()
        count = 0
        
        for user in queryset.filter(email_verified=False):
            user.generate_email_verification_token()
            if email_service.send_verification_email(user):
                count += 1
        
        self.message_user(request, f'Verification emails sent to {count} users.')
    send_verification_emails.short_description = "Send verification emails"

    def unlock_accounts(self, request, queryset):
        """Unlock selected user accounts."""
        for user in queryset.filter(is_locked=True):
            user.unlock_account()
        
        count = queryset.filter(is_locked=True).count()
        self.message_user(request, f'{count} accounts unlocked.')
    unlock_accounts.short_description = "Unlock accounts"

    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users deactivated.')
    deactivate_users.short_description = "Deactivate users"

    def activate_users(self, request, queryset):
        """Activate selected users."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users activated.')
    activate_users.short_description = "Activate users"

    def reset_failed_attempts(self, request, queryset):
        """Reset failed login attempts for selected users."""
        updated = queryset.update(failed_login_attempts=0)
        self.message_user(request, f'Failed attempts reset for {updated} users.')
    reset_failed_attempts.short_description = "Reset failed login attempts"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin for user profiles."""
    
    list_display = [
        'user_email', 'business_type', 'years_in_business', 'number_of_machines',
        'completion_percentage_display', 'profile_completed', 'updated_at'
    ]
    
    list_filter = [
        'business_type', 'profile_completed', 'country', 'preferred_contact_method',
        'created_at', 'updated_at'
    ]
    
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'address_line1', 'city', 'state', 'zip_code'
    ]
    
    readonly_fields = ['user_email', 'completion_percentage_display', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_email')
        }),
        ('Business Information', {
            'fields': ('business_type', 'years_in_business', 'number_of_machines', 'target_locations')
        }),
        ('Address Information', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country')
        }),
        ('Social Media', {
            'fields': ('linkedin_url', 'twitter_url', 'facebook_url'),
            'classes': ('collapse',)
        }),
        ('Preferences & Status', {
            'fields': ('preferred_contact_method', 'profile_completed', 'completion_percentage_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def completion_percentage_display(self, obj):
        """Display completion percentage with color."""
        percentage = obj.completion_percentage
        color = '#28a745' if percentage >= 80 else '#ffc107' if percentage >= 50 else '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, percentage
        )
    completion_percentage_display.short_description = 'Completion'

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin for user activities."""
    
    list_display = [
        'user_email', 'activity_type_display', 'description_short', 
        'ip_address', 'created_at_display'
    ]
    
    list_filter = [
        'activity_type', 'created_at'
    ]
    
    search_fields = [
        'user__email', 'description', 'ip_address'
    ]
    
    readonly_fields = [
        'user', 'activity_type', 'description', 'ip_address', 
        'user_agent', 'metadata', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    
    ordering = ['-created_at']

    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def activity_type_display(self, obj):
        """Display activity type with color coding."""
        colors = {
            'login': '#28a745',
            'logout': '#6c757d',
            'registration': '#17a2b8',
            'password_change': '#ffc107',
            'email_change': '#fd7e14',
            'profile_update': '#20c997',
        }
        color = colors.get(obj.activity_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_activity_type_display()
        )
    activity_type_display.short_description = 'Activity'

    def description_short(self, obj):
        """Display truncated description."""
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'

    def created_at_display(self, obj):
        """Display formatted creation date."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    created_at_display.short_description = 'Date'
    created_at_display.admin_order_field = 'created_at'

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user')

    def has_add_permission(self, request):
        """Disable manual addition of activities."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing of activities."""
        return False