from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from django.utils import timezone
from .models import (
    LeadCreditPackage, PaymentHistory, UserLeadCredit,
    SubscriptionUpgradeRequest, SubscriptionCancellationRequest
)


@admin.register(LeadCreditPackage)
class LeadCreditPackageAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'lead_count', 'price', 'price_per_lead_display',
        'target_buyer_plan', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'target_buyer_plan', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'price_per_lead_display']
    
    fieldsets = (
        ('Package Information', {
            'fields': ('name', 'description', 'price', 'lead_count')
        }),
        ('Targeting', {
            'fields': ('target_buyer_plan',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('price_per_lead_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def price_per_lead_display(self, obj):
        return f"${obj.price_per_lead}"
    price_per_lead_display.short_description = 'Price per Lead'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('target_buyer_plan')


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'user_link', 'amount_display', 'payment_gateway',
        'status_display', 'subscription_link', 'package_link', 'created_at'
    ]
    list_filter = [
        'payment_gateway', 'status', 'currency', 'created_at'
    ]
    search_fields = [
        'transaction_id', 'gateway_transaction_id', 'user__email',
        'user__first_name', 'user__last_name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'transaction_id'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Transaction Information', {
            'fields': ('transaction_id', 'gateway_transaction_id', 'amount', 'currency')
        }),
        ('Related Objects', {
            'fields': ('user', 'subscription', 'package_purchased')
        }),
        ('Payment Details', {
            'fields': ('payment_gateway', 'status', 'failure_reason')
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__email'

    def amount_display(self, obj):
        return f"${obj.amount} {obj.currency}"
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def status_display(self, obj):
        colors = {
            'completed': '#28a745',
            'pending': '#ffc107',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#fd7e14',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def subscription_link(self, obj):
        if obj.subscription:
            url = reverse('admin:project_core_usersubscription_change', args=[obj.subscription.pk])
            return format_html('<a href="{}">{}</a>', url, obj.subscription.plan.name)
        return '-'
    subscription_link.short_description = 'Subscription'

    def package_link(self, obj):
        if obj.package_purchased:
            url = reverse('admin:subscriptions_leadcreditpackage_change', args=[obj.package_purchased.pk])
            return format_html('<a href="{}">{}</a>', url, obj.package_purchased.name)
        return '-'
    package_link.short_description = 'Package'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'subscription__plan', 'package_purchased'
        )

    actions = ['mark_as_completed', 'mark_as_failed']

    def mark_as_completed(self, request, queryset):
        updated = 0
        for payment in queryset.filter(status='pending'):
            payment.mark_completed()
            updated += 1
        self.message_user(request, f'{updated} payments marked as completed.')

    def mark_as_failed(self, request, queryset):
        updated = 0
        for payment in queryset.filter(status='pending'):
            payment.mark_failed('Manually marked as failed')
            updated += 1
        self.message_user(request, f'{updated} payments marked as failed.')

    mark_as_completed.short_description = "Mark selected payments as completed"
    mark_as_failed.short_description = "Mark selected payments as failed"


@admin.register(UserLeadCredit)
class UserLeadCreditAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'package_link', 'credits_display', 'expires_at',
        'is_expired_display', 'created_at'
    ]
    list_filter = ['expires_at', 'created_at', 'package']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'credits_remaining_display']

    fieldsets = (
        ('Credit Information', {
            'fields': ('user', 'package', 'payment')
        }),
        ('Credit Usage', {
            'fields': ('credits_purchased', 'credits_used', 'credits_remaining_display')
        }),
        ('Expiration', {
            'fields': ('expires_at',)
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

    def package_link(self, obj):
        url = reverse('admin:subscriptions_leadcreditpackage_change', args=[obj.package.pk])
        return format_html('<a href="{}">{}</a>', url, obj.package.name)
    package_link.short_description = 'Package'

    def credits_display(self, obj):
        return f"{obj.credits_remaining}/{obj.credits_purchased}"
    credits_display.short_description = 'Credits (Used/Total)'

    def credits_remaining_display(self, obj):
        return obj.credits_remaining
    credits_remaining_display.short_description = 'Credits Remaining'

    def is_expired_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: #dc3545;">Expired</span>')
        return format_html('<span style="color: #28a745;">Active</span>')
    is_expired_display.short_description = 'Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'package', 'payment')


@admin.register(SubscriptionUpgradeRequest)
class SubscriptionUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'current_plan', 'requested_plan', 'status_display',
        'proration_amount', 'effective_date', 'created_at'
    ]
    list_filter = ['status', 'effective_date', 'created_at']
    search_fields = ['user__email', 'notes']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'current_subscription', 'requested_plan')
        }),
        ('Status & Timing', {
            'fields': ('status', 'effective_date', 'proration_amount')
        }),
        ('Notes', {
            'fields': ('notes',)
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

    def current_plan(self, obj):
        return obj.current_subscription.plan.name
    current_plan.short_description = 'Current Plan'

    def status_display(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#17a2b8',
            'completed': '#28a745',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'current_subscription__plan', 'requested_plan'
        )


@admin.register(SubscriptionCancellationRequest)
class SubscriptionCancellationRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'subscription_plan', 'reason_display', 'cancel_immediately',
        'cancellation_date', 'is_processed', 'created_at'
    ]
    list_filter = ['reason', 'cancel_immediately', 'is_processed', 'created_at']
    search_fields = ['user__email', 'feedback']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Cancellation Request', {
            'fields': ('user', 'subscription', 'reason', 'feedback')
        }),
        ('Cancellation Details', {
            'fields': ('cancel_immediately', 'cancellation_date', 'is_processed')
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

    def subscription_plan(self, obj):
        return obj.subscription.plan.name
    subscription_plan.short_description = 'Plan'

    def reason_display(self, obj):
        return obj.get_reason_display()
    reason_display.short_description = 'Reason'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'subscription__plan')

    actions = ['mark_as_processed']

    def mark_as_processed(self, request, queryset):
        updated = queryset.update(is_processed=True)
        self.message_user(request, f'{updated} cancellation requests marked as processed.')

    mark_as_processed.short_description = "Mark selected requests as processed"