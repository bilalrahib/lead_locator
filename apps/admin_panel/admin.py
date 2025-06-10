from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.utils import timezone
from .models import AdminLog, ContentTemplate, SystemSettings, AdminDashboardStats


@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    """Admin interface for admin logs."""
    
    list_display = [
        'created_at', 'admin_user_link', 'action_type_display', 
        'target_user_link', 'description_short', 'ip_address'
    ]
    list_filter = ['action_type', 'created_at']
    search_fields = [
        'admin_user__email', 'target_user__email', 'description'
    ]
    readonly_fields = [
        'id', 'admin_user', 'action_type', 'target_user', 'description',
        'before_state', 'after_state', 'ip_address', 'user_agent',
        'metadata', 'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50

    fieldsets = (
        ('Action Information', {
            'fields': ('admin_user', 'action_type', 'target_user', 'description')
        }),
        ('State Changes', {
            'fields': ('before_state', 'after_state'),
            'classes': ('collapse',)
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def admin_user_link(self, obj):
        """Link to admin user."""
        if hasattr(obj.admin_user, 'pk'):
            url = reverse('admin:accounts_customuser_change', args=[obj.admin_user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.admin_user.email)
        return obj.admin_user.email
    admin_user_link.short_description = 'Admin User'
    admin_user_link.admin_order_field = 'admin_user__email'

    def target_user_link(self, obj):
        """Link to target user."""
        if obj.target_user and hasattr(obj.target_user, 'pk'):
            url = reverse('admin:accounts_customuser_change', args=[obj.target_user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.target_user.email)
        elif obj.target_user:
            return obj.target_user.email
        return '-'
    target_user_link.short_description = 'Target User'

    def action_type_display(self, obj):
        """Display action type with color coding."""
        colors = {
            'user_activate': '#28a745',
            'user_deactivate': '#dc3545',
            'subscription_change': '#17a2b8',
            'credit_grant': '#ffc107',
            'content_create': '#20c997',
            'content_update': '#fd7e14',
            'content_delete': '#dc3545',
            'system_setting': '#6f42c1',
        }
        color = colors.get(obj.action_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_action_type_display()
        )
    action_type_display.short_description = 'Action'

    def description_short(self, obj):
        """Truncated description."""
        return (obj.description[:50] + '...') if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('admin_user', 'target_user')

    def has_add_permission(self, request):
        """Disable manual creation of logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make logs read-only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup."""
        return request.user.is_superuser


@admin.register(ContentTemplate)
class ContentTemplateAdmin(admin.ModelAdmin):
    """Admin interface for content templates."""
    
    list_display = [
        'name', 'template_type_display', 'status_display', 'is_featured',
        'usage_count', 'created_by_link', 'created_at'
    ]
    list_filter = ['template_type', 'status', 'is_featured', 'created_at']
    search_fields = ['name', 'title', 'description', 'tags']
    readonly_fields = ['id', 'usage_count', 'created_by', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'template_type', 'title', 'description')
        }),
        ('Content', {
            'fields': ('content', 'preview_url', 'thumbnail')
        }),
        ('Settings', {
            'fields': ('status', 'is_featured', 'tags')
        }),
        ('Metadata', {
            'fields': ('usage_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def template_type_display(self, obj):
        """Display template type with icon."""
        icons = {
            'email': '📧',
            'social_post': '📱',
            'banner': '🖼️',
            'tutorial': '📚',
            'landing_page': '🌐',
            'video': '🎥',
        }
        icon = icons.get(obj.template_type, '📄')
        return f"{icon} {obj.get_template_type_display()}"
    template_type_display.short_description = 'Type'

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'draft': '#6c757d',
            'active': '#28a745',
            'archived': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def created_by_link(self, obj):
        """Link to creator."""
        if hasattr(obj.created_by, 'pk'):
            url = reverse('admin:accounts_customuser_change', args=[obj.created_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.created_by.get_full_name() or obj.created_by.email)
        return obj.created_by.get_full_name() or obj.created_by.email
    created_by_link.short_description = 'Created By'

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('created_by')

    def save_model(self, request, obj, form, change):
        """Set created_by to current user."""
        if not change:  # Only for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    actions = ['mark_active', 'mark_featured', 'mark_archived']

    def mark_active(self, request, queryset):
        """Mark templates as active."""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} templates marked as active.')

    def mark_featured(self, request, queryset):
        """Mark templates as featured."""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} templates marked as featured.')

    def mark_archived(self, request, queryset):
        """Archive templates."""
        updated = queryset.update(status='archived')
        self.message_user(request, f'{updated} templates archived.')

    mark_active.short_description = "Mark selected templates as active"
    mark_featured.short_description = "Mark selected templates as featured"
    mark_archived.short_description = "Archive selected templates"


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """Admin interface for system settings."""
    
    list_display = [
        'key', 'value_display', 'setting_type', 'category',
        'is_active', 'is_editable', 'updated_by_link', 'updated_at'
    ]
    list_filter = ['setting_type', 'category', 'is_active', 'is_editable']
    search_fields = ['key', 'description', 'value']
    readonly_fields = ['id', 'created_at', 'updated_at', 'updated_by']

    fieldsets = (
        ('Setting Information', {
            'fields': ('key', 'value', 'setting_type', 'description')
        }),
        ('Configuration', {
            'fields': ('category', 'is_active', 'is_editable')
        }),
        ('Metadata', {
            'fields': ('updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def value_display(self, obj):
        """Display truncated value."""
        value = str(obj.value)
        if len(value) > 50:
            return value[:50] + '...'
        return value
    value_display.short_description = 'Value'

    def updated_by_link(self, obj):
        """Link to user who updated."""
        if obj.updated_by and hasattr(obj.updated_by, 'pk'):
            url = reverse('admin:accounts_customuser_change', args=[obj.updated_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.updated_by.get_full_name() or obj.updated_by.email)
        elif obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.email
        return '-'
    updated_by_link.short_description = 'Updated By'

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('updated_by')

    def save_model(self, request, obj, form, change):
        """Track who updated the setting."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AdminDashboardStats)
class AdminDashboardStatsAdmin(admin.ModelAdmin):
    """Admin interface for dashboard stats - simplified version."""
    
    list_display = [
        'stat_date', 'total_users', 'revenue_today', 'updated_at'
    ]
    list_filter = ['stat_date']
    readonly_fields = [
        'stat_date', 'total_users', 'new_users_today', 'active_subscriptions',
        'revenue_today', 'searches_today', 'support_tickets_open',
        'cache_data', 'created_at', 'updated_at'
    ]
    ordering = ['-stat_date']

    fieldsets = (
        ('Date', {
            'fields': ('stat_date',)
        }),
        ('User Statistics', {
            'fields': ('total_users', 'new_users_today')
        }),
        ('Business Statistics', {
            'fields': ('active_subscriptions', 'revenue_today', 'searches_today', 'support_tickets_open')
        }),
        ('System Data', {
            'fields': ('cache_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        """Stats are auto-generated."""
        return False

    def has_change_permission(self, request, obj=None):
        """Stats are read-only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow superusers to delete old stats."""
        return request.user.is_superuser