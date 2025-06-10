from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from .models import SearchHistory, LocationData, UserLocationPreference, ExcludedLocation


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'zip_code', 'machine_type_display', 'radius',
        'results_count', 'created_at'
    ]
    list_filter = ['machine_type', 'radius', 'created_at']
    search_fields = ['user__email', 'zip_code']
    readonly_fields = ['id', 'results_count', 'search_parameters', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Search Details', {
            'fields': ('user', 'zip_code', 'radius', 'machine_type')
        }),
        ('Filters', {
            'fields': ('building_types_filter',)
        }),
        ('Results', {
            'fields': ('results_count', 'search_parameters')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def machine_type_display(self, obj):
        return obj.get_machine_type_display()
    machine_type_display.short_description = 'Machine Type'
    machine_type_display.admin_order_field = 'machine_type'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


class LocationDataInline(admin.TabularInline):
    model = LocationData
    extra = 0
    readonly_fields = ['name', 'address', 'priority_score', 'contact_completeness']
    fields = ['name', 'address', 'phone', 'email', 'priority_score', 'contact_completeness']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LocationData)
class LocationDataAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'address_short', 'contact_info', 'google_rating',
        'foot_traffic_estimate', 'priority_score', 'search_user'
    ]
    list_filter = [
        'foot_traffic_estimate', 'contact_completeness', 'google_business_status',
        'created_at'
    ]
    search_fields = ['name', 'address', 'phone', 'email', 'google_place_id']
    readonly_fields = [
        'id', 'coordinates', 'priority_score', 'contact_completeness',
        'osm_data', 'google_data', 'created_at', 'updated_at'
    ]
    ordering = ['-priority_score', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('search_history', 'name', 'category', 'detailed_category', 'address')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'coordinates')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'website', 'business_hours_text')
        }),
        ('Google Data', {
            'fields': ('google_place_id', 'google_rating', 'google_user_ratings_total',
                      'google_business_status', 'maps_url')
        }),
        ('Analysis', {
            'fields': ('foot_traffic_estimate', 'priority_score', 'contact_completeness')
        }),
        ('Raw Data', {
            'fields': ('osm_data', 'google_data'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def address_short(self, obj):
        return obj.address[:50] + '...' if len(obj.address) > 50 else obj.address
    address_short.short_description = 'Address'

    def contact_info(self, obj):
        parts = []
        if obj.phone:
            parts.append('📞')
        if obj.email:
            parts.append('📧')
        if obj.website:
            parts.append('🌐')
        return ' '.join(parts) if parts else '❌'
    contact_info.short_description = 'Contact'

    def search_user(self, obj):
        return obj.search_history.user.email
    search_user.short_description = 'User'
    search_user.admin_order_field = 'search_history__user__email'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('search_history__user')

    actions = ['recalculate_priority_scores']

    def recalculate_priority_scores(self, request, queryset):
        updated = 0
        for location in queryset:
            location.calculate_priority_score()
            location.save(update_fields=['priority_score', 'contact_completeness'])
            updated += 1
        
        self.message_user(request, f'{updated} location priority scores recalculated.')
    recalculate_priority_scores.short_description = "Recalculate priority scores"


@admin.register(UserLocationPreference)
class UserLocationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'preferred_radius', 'minimum_rating', 'require_contact_info',
        'updated_at'
    ]
    list_filter = ['preferred_radius', 'require_contact_info', 'minimum_rating']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Search Preferences', {
            'fields': ('preferred_machine_types', 'preferred_radius', 'preferred_building_types')
        }),
        ('Filters', {
            'fields': ('excluded_categories', 'minimum_rating', 'require_contact_info')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(ExcludedLocation)
class ExcludedLocationAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'location_name', 'reason_display', 'created_at'
    ]
    list_filter = ['reason', 'created_at']
    search_fields = [
        'user__email', 'location_name', 'google_place_id', 'notes'
    ]
    readonly_fields = ['created_at']

    fieldsets = (
        ('Exclusion Details', {
            'fields': ('user', 'google_place_id', 'location_name')
        }),
        ('Reason', {
            'fields': ('reason', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def reason_display(self, obj):
        return obj.get_reason_display()
    reason_display.short_description = 'Reason'
    reason_display.admin_order_field = 'reason'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')