from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ManagedLocation, PlacedMachine, VisitLog, CollectionData


@admin.register(ManagedLocation)
class ManagedLocationAdmin(admin.ModelAdmin):
    list_display = [
        'location_name', 'user_link', 'total_machines', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['location_name', 'user__email', 'address_details']
    readonly_fields = ['id', 'total_machines', 'total_revenue_this_month', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'location_name', 'address_details', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'contact_phone', 'contact_email')
        }),
        ('Location Details', {
            'fields': ('latitude', 'longitude', 'image', 'notes')
        }),
        ('Statistics', {
            'fields': ('total_machines', 'total_revenue_this_month'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
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


@admin.register(PlacedMachine)
class PlacedMachineAdmin(admin.ModelAdmin):
    list_display = [
        'machine_type', 'machine_identifier', 'location_link', 'date_placed', 'is_active'
    ]
    list_filter = ['machine_type', 'is_active', 'date_placed']
    search_fields = [
        'machine_identifier', 'managed_location__location_name', 
        'managed_location__user__email'
    ]
    readonly_fields = [
        'id', 'total_collections_this_month', 'average_per_visit', 
        'days_since_placement', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('managed_location', 'machine_type', 'machine_identifier', 'date_placed', 'is_active')
        }),
        ('Financial Details', {
            'fields': ('commission_percentage_to_location', 'vend_price_range', 'cost_per_vend')
        }),
        ('Additional Information', {
            'fields': ('image', 'notes')
        }),
        ('Performance Metrics', {
            'fields': ('total_collections_this_month', 'average_per_visit', 'days_since_placement'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def location_link(self, obj):
        url = reverse('admin:operations_managedlocation_change', args=[obj.managed_location.pk])
        return format_html('<a href="{}">{}</a>', url, obj.managed_location.location_name)
    location_link.short_description = 'Location'
    location_link.admin_order_field = 'managed_location__location_name'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('managed_location')


@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    list_display = [
        'machine_link', 'visit_type', 'visit_date', 'total_collected'
    ]
    list_filter = ['visit_type', 'visit_date']
    search_fields = [
        'placed_machine__machine_identifier',
        'placed_machine__managed_location__location_name',
        'notes'
    ]
    readonly_fields = ['id', 'total_collected', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Visit Information', {
            'fields': ('placed_machine', 'visit_date', 'visit_type')
        }),
        ('Details', {
            'fields': ('notes',)
        }),
        ('Collection Summary', {
            'fields': ('total_collected',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def machine_link(self, obj):
        url = reverse('admin:operations_placedmachine_change', args=[obj.placed_machine.pk])
        return format_html('<a href="{}">{} at {}</a>', 
                         url, 
                         obj.placed_machine.get_machine_type_display(),
                         obj.placed_machine.managed_location.location_name)
    machine_link.short_description = 'Machine'
    machine_link.admin_order_field = 'placed_machine__machine_type'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'placed_machine',
            'placed_machine__managed_location'
        )


@admin.register(CollectionData)
class CollectionDataAdmin(admin.ModelAdmin):
    list_display = [
        'visit_link', 'cash_collected', 'commission_paid_to_location', 
        'net_profit', 'profit_margin', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'visit_log__placed_machine__machine_identifier',
        'visit_log__placed_machine__managed_location__location_name',
        'restock_notes'
    ]
    readonly_fields = ['id', 'net_profit', 'profit_margin', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Collection Information', {
            'fields': ('visit_log', 'cash_collected', 'items_sold_value')
        }),
        ('Expenses', {
            'fields': ('commission_paid_to_location', 'restock_cost', 'maintenance_cost')
        }),
        ('Notes', {
            'fields': ('restock_notes',)
        }),
        ('Financial Analysis', {
            'fields': ('net_profit', 'profit_margin'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def visit_link(self, obj):
        url = reverse('admin:operations_visitlog_change', args=[obj.visit_log.pk])
        return format_html('<a href="{}">{} - {}</a>',url, 
                         obj.visit_log.get_visit_type_display(),
                         obj.visit_log.visit_date.strftime('%Y-%m-%d'))
    visit_link.short_description = 'Visit'
    visit_link.admin_order_field = 'visit_log__visit_date'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'visit_log',
            'visit_log__placed_machine',
            'visit_log__placed_machine__managed_location'
        )