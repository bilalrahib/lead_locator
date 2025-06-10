from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import ClientProfile, ClientSavedSearch, ClientLocationData, WhiteLabelSettings


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = [
        'client_name', 'user_link', 'client_contact_name', 'client_zip_code',
        'default_machine_type_display', 'total_searches_count', 'is_active', 'created_at'
    ]
    list_filter = ['default_machine_type', 'is_active', 'client_state', 'created_at']
    search_fields = [
        'client_name', 'client_contact_name', 'client_email', 'client_zip_code',
        'user__email', 'user__first_name', 'user__last_name'
    ]
    readonly_fields = ['id', 'total_searches_count', 'total_locations_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Owner Information', {
            'fields': ('user',)
        }),
        ('Client Information', {
            'fields': ('client_name', 'client_contact_name', 'client_email', 'client_phone')
        }),
        ('Location Details', {
            'fields': ('client_zip_code', 'client_city', 'client_state')
        }),
        ('Preferences', {
            'fields': ('default_machine_type', 'client_notes')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Statistics', {
            'fields': ('total_searches_count', 'total_locations_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def default_machine_type_display(self, obj):
        return obj.get_default_machine_type_display()
    default_machine_type_display.short_description = 'Machine Type'
    default_machine_type_display.admin_order_field = 'default_machine_type'

    def total_searches_count(self, obj):
        return obj.total_searches
    total_searches_count.short_description = 'Total Searches'

    def total_locations_count(self, obj):
        return obj.total_locations_found
    total_locations_count.short_description = 'Total Locations'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').annotate(
            searches_count=Count('saved_searches', distinct=True),
            locations_count=Count('client_locations', distinct=True)
        )

    actions = ['activate_clients', 'deactivate_clients']

    def activate_clients(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} clients activated.')

    def deactivate_clients(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} clients deactivated.')

    activate_clients.short_description = "Activate selected clients"
    deactivate_clients.short_description = "Deactivate selected clients"


@admin.register(ClientSavedSearch)
class ClientSavedSearchAdmin(admin.ModelAdmin):
    list_display = [
        'search_name', 'client_link', 'user_link', 'search_summary',
        'locations_count', 'is_shared_with_client', 'shared_at', 'created_at'
    ]
    list_filter = ['is_shared_with_client', 'created_at', 'shared_at']
    search_fields = [
        'search_name', 'notes', 'client_profile__client_name',
        'client_profile__user__email', 'search_history__zip_code'
    ]
    readonly_fields = ['id', 'search_summary', 'locations_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Search Information', {
            'fields': ('client_profile', 'search_history', 'search_name', 'notes')
        }),
        ('Sharing Status', {
            'fields': ('is_shared_with_client', 'shared_at')
        }),
        ('Statistics', {
            'fields': ('search_summary', 'locations_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def client_link(self, obj):
        url = reverse('admin:pro_locator_clientprofile_change', args=[obj.client_profile.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client_profile.client_name)
    client_link.short_description = 'Client'
    client_link.admin_order_field = 'client_profile__client_name'

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.client_profile.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client_profile.user.email)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'client_profile__user__email'

    def search_summary(self, obj):
        return obj.search_history.search_summary
    search_summary.short_description = 'Search Summary'

    def locations_count(self, obj):
        return obj.assigned_locations.count()
    locations_count.short_description = 'Locations'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client_profile__user', 'search_history'
        ).prefetch_related('assigned_locations')

    actions = ['mark_as_shared']

    def mark_as_shared(self, request, queryset):
        updated = 0
        for search in queryset:
            if not search.is_shared_with_client:
                search.mark_shared()
                updated += 1
        self.message_user(request, f'{updated} searches marked as shared.')

    mark_as_shared.short_description = "Mark selected searches as shared"


@admin.register(ClientLocationData)
class ClientLocationDataAdmin(admin.ModelAdmin):
    list_display = [
        'location_name', 'client_link', 'status_display', 'priority',
        'location_address', 'contact_info', 'created_at'
    ]
    list_filter = ['status', 'priority', 'created_at']
    search_fields = [
        'location_data__name', 'location_data__address', 'client_profile__client_name',
        'notes', 'client_profile__user__email'
    ]
    readonly_fields = ['id', 'location_address', 'contact_info', 'created_at', 'updated_at']
    ordering = ['-priority', '-created_at']

    fieldsets = (
        ('Assignment', {
            'fields': ('client_profile', 'location_data', 'saved_search')
        }),
        ('Client Management', {
            'fields': ('status', 'priority', 'notes')
        }),
        ('Location Details', {
            'fields': ('location_address', 'contact_info'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def location_name(self, obj):
        return obj.location_data.name
    location_name.short_description = 'Location'
    location_name.admin_order_field = 'location_data__name'

    def client_link(self, obj):
        url = reverse('admin:pro_locator_clientprofile_change', args=[obj.client_profile.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client_profile.client_name)
    client_link.short_description = 'Client'
    client_link.admin_order_field = 'client_profile__client_name'

    def status_display(self, obj):
        colors = {
            'new': '#17a2b8',
            'contacted': '#ffc107',
            'interested': '#28a745',
            'not_interested': '#6c757d',
            'placed': '#28a745',
            'rejected': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def location_address(self, obj):
        return obj.location_data.address
    location_address.short_description = 'Address'

    def contact_info(self, obj):
        parts = []
        if obj.location_data.phone:
            parts.append('📞')
        if obj.location_data.email:
            parts.append('📧')
        return ' '.join(parts) if parts else '❌'
    contact_info.short_description = 'Contact'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client_profile', 'location_data', 'saved_search'
        )


@admin.register(WhiteLabelSettings)
class WhiteLabelSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'company_name', 'has_logo', 'primary_color',
        'remove_vending_hive_branding', 'is_active', 'updated_at'
    ]
    list_filter = ['remove_vending_hive_branding', 'is_active', 'created_at']
    search_fields = ['user__email', 'company_name', 'company_website']
    readonly_fields = ['id', 'has_custom_branding_display', 'created_at', 'updated_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Company Branding', {
            'fields': ('company_name', 'company_logo', 'primary_color', 'secondary_color')
        }),
        ('Contact Information', {
            'fields': ('company_website', 'company_phone', 'company_email')
        }),
        ('Advanced Options', {
            'fields': ('custom_domain', 'remove_vending_hive_branding')
        }),
        ('Status', {
            'fields': ('is_active', 'has_custom_branding_display')
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def has_logo(self, obj):
        if obj.company_logo:
            return format_html('<span style="color: #28a745;">✓</span>')
        return format_html('<span style="color: #dc3545;">✗</span>')
    has_logo.short_description = 'Logo'

    def has_custom_branding_display(self, obj):
        if obj.has_custom_branding:
            return format_html('<span style="color: #28a745;">Yes</span>')
        return format_html('<span style="color: #dc3545;">No</span>')
    has_custom_branding_display.short_description = 'Custom Branding'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')