from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import SupportTicket, WeatherLocation, SystemNotification, ContactMessage, SubscriptionPlan


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'user_link', 'subject', 'priority', 'status', 'created_at', 'is_open']
    list_filter = ['priority', 'status', 'created_at']
    search_fields = ['user__username', 'user__email', 'subject', 'description']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 25
    
    fieldsets = (
        (None, {
            'fields': ('user', 'subject', 'description')
        }),
        ('Status & Priority', {
            'fields': ('priority', 'status', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )

    def ticket_id(self, obj):
        return f"#{obj.id.hex[:8]}"
    ticket_id.short_description = 'Ticket ID'

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user')

    actions = ['mark_resolved', 'mark_in_progress', 'mark_closed']

    def mark_resolved(self, request, queryset):
        updated = queryset.update(status='resolved')
        self.message_user(request, f'{updated} tickets marked as resolved.')

    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} tickets marked as in progress.')

    def mark_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} tickets marked as closed.')

    mark_resolved.short_description = "Mark selected tickets as resolved"
    mark_in_progress.short_description = "Mark selected tickets as in progress"
    mark_closed.short_description = "Mark selected tickets as closed"


@admin.register(WeatherLocation)
class WeatherLocationAdmin(admin.ModelAdmin):
    list_display = ['user', 'address', 'city', 'state', 'zip_code', 'coordinates_display', 'updated_at']
    search_fields = ['user__username', 'address', 'city', 'zip_code']
    readonly_fields = ['created_at', 'updated_at', 'coordinates_display']
    list_filter = ['state', 'country', 'updated_at']

    def coordinates_display(self, obj):
        if obj.latitude and obj.longitude:
            return f"{obj.latitude}, {obj.longitude}"
        return "Not set"
    coordinates_display.short_description = 'Coordinates'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user')


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'is_active', 'show_on_homepage', 'start_date', 'end_date', 'is_current']
    list_filter = ['notification_type', 'is_active', 'show_on_homepage', 'start_date']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at', 'updated_at', 'is_current']
    date_hierarchy = 'start_date'
    ordering = ['-created_at']

    fieldsets = (
        (None, {
            'fields': ('title', 'message', 'notification_type')
        }),
        ('Visibility', {
            'fields': ('is_active', 'show_on_homepage')
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'is_current'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_notifications', 'deactivate_notifications']

    def activate_notifications(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} notifications activated.')

    def deactivate_notifications(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} notifications deactivated.')

    activate_notifications.short_description = "Activate selected notifications"
    deactivate_notifications.short_description = "Deactivate selected notifications"


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'ip_address', 'user_agent']
    ordering = ['-created_at']

    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Message', {
            'fields': ('subject', 'message')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} messages marked as read.')

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} messages marked as unread.')

    mark_as_read.short_description = "Mark selected messages as read"
    mark_as_unread.short_description = "Mark selected messages as unread"


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'leads_per_month', 'script_templates_count', 'is_active', 'is_free', 'is_premium']
    list_filter = ['name', 'is_active', 'regeneration_allowed']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'is_free', 'is_premium']
    ordering = ['price']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'price')
        }),
        ('Features', {
            'fields': ('leads_per_month', 'leads_per_search_range', 'script_templates_count', 'regeneration_allowed')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('is_free', 'is_premium', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            user_count=Count('usersubscription', distinct=True)
        )