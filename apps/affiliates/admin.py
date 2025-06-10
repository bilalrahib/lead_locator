from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from .models import AffiliateProfile, ReferralClick, ReferralConversion, CommissionLedger, AffiliateResource


@admin.register(AffiliateProfile)
class AffiliateProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'referral_code', 'status_display', 'commission_rate',
        'total_conversions', 'total_earnings', 'approved_at', 'created_at'
    ]
    list_filter = ['status', 'payout_method', 'approved_at', 'created_at']
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'referral_code', 'website_url'
    ]
    readonly_fields = [
        'id', 'referral_code', 'applied_at', 'approved_at', 'approved_by',
        'created_at', 'updated_at', 'total_conversions', 'total_earnings',
        'pending_earnings'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'referral_code', 'status')
        }),
        ('Application Details', {
            'fields': (
                'application_reason', 'marketing_experience', 'traffic_sources',
                'website_url'
            )
        }),
        ('Commission Settings', {
            'fields': ('commission_rate', 'minimum_payout')
        }),
        ('Payout Information', {
            'fields': (
                'payout_method', 'paypal_email', 'stripe_connect_id',
                'bank_account_details'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_conversions', 'total_earnings', 'pending_earnings'),
            'classes': ('collapse',)
        }),
        ('Status Tracking', {
            'fields': ('applied_at', 'approved_at', 'approved_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.full_name)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__first_name'

    def status_display(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'suspended': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def total_conversions(self, obj):
        return obj.conversions.count()
    total_conversions.short_description = 'Conversions'

    def total_earnings(self, obj):
        return f"${obj.get_total_earnings():.2f}"
    total_earnings.short_description = 'Total Earnings'

    def pending_earnings(self, obj):
        return f"${obj.get_pending_earnings():.2f}"
    pending_earnings.short_description = 'Pending Earnings'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'approved_by'
        ).prefetch_related('conversions', 'commission_ledger')

    actions = ['approve_affiliates', 'reject_affiliates', 'suspend_affiliates']

    def approve_affiliates(self, request, queryset):
        for affiliate in queryset.filter(status='pending'):
            affiliate.approve(request.user)
        self.message_user(request, f'Approved {queryset.count()} affiliates.')

    def reject_affiliates(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'Rejected {updated} affiliates.')

    def suspend_affiliates(self, request, queryset):
        for affiliate in queryset.filter(status='approved'):
            affiliate.suspend()
        self.message_user(request, f'Suspended {queryset.count()} affiliates.')

    approve_affiliates.short_description = "Approve selected affiliates"
    reject_affiliates.short_description = "Reject selected affiliates"
    suspend_affiliates.short_description = "Suspend selected affiliates"


@admin.register(ReferralClick)
class ReferralClickAdmin(admin.ModelAdmin):
    list_display = [
        'affiliate_code', 'ip_address', 'timestamp', 'has_conversion',
        'referrer_domain', 'landing_page_display'
    ]
    list_filter = ['timestamp', 'affiliate__status']
    search_fields = ['affiliate__referral_code', 'ip_address', 'referrer_url']
    readonly_fields = [
        'id', 'affiliate', 'ip_address', 'user_agent', 'referrer_url',
        'landing_page', 'session_key', 'timestamp'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def affiliate_code(self, obj):
        return obj.affiliate.referral_code
    affiliate_code.short_description = 'Affiliate Code'
    affiliate_code.admin_order_field = 'affiliate__referral_code'

    def has_conversion(self, obj):
        return hasattr(obj, 'conversion') and obj.conversion is not None
    has_conversion.boolean = True
    has_conversion.short_description = 'Converted'

    def referrer_domain(self, obj):
        if obj.referrer_url:
            from urllib.parse import urlparse
            return urlparse(obj.referrer_url).netloc
        return '-'
    referrer_domain.short_description = 'Referrer Domain'

    def landing_page_display(self, obj):
        if obj.landing_page:
            return obj.landing_page[:50] + '...' if len(obj.landing_page) > 50 else obj.landing_page
        return '-'
    landing_page_display.short_description = 'Landing Page'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('affiliate')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReferralConversion)
class ReferralConversionAdmin(admin.ModelAdmin):
    list_display = [
        'affiliate_code', 'referred_user_link', 'conversion_value',
        'has_subscription', 'timestamp'
    ]
    list_filter = ['timestamp', 'affiliate__status']
    search_fields = [
        'affiliate__referral_code', 'referred_user__email',
        'referred_user__first_name', 'referred_user__last_name'
    ]
    readonly_fields = [
        'id', 'affiliate', 'referred_user', 'referral_click',
        'conversion_value', 'timestamp'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def affiliate_code(self, obj):
        return obj.affiliate.referral_code
    affiliate_code.short_description = 'Affiliate Code'
    affiliate_code.admin_order_field = 'affiliate__referral_code'

    def referred_user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.referred_user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.referred_user.full_name)
    referred_user_link.short_description = 'Referred User'

    def has_subscription(self, obj):
        return hasattr(obj.referred_user, 'subscription') and obj.referred_user.subscription.is_active
    has_subscription.boolean = True
    has_subscription.short_description = 'Has Subscription'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'affiliate', 'referred_user', 'referral_click'
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CommissionLedger)
class CommissionLedgerAdmin(admin.ModelAdmin):
    list_display = [
        'affiliate_code', 'month_year', 'subscription_amount',
        'amount_earned', 'status_display', 'paid_at'
    ]
    list_filter = ['status', 'month_year', 'payout_method', 'created_at']
    search_fields = [
        'affiliate__referral_code', 'affiliate__user__email',
        'referred_user_subscription__user__email'
    ]
    readonly_fields = [
        'id', 'affiliate', 'referred_user_subscription', 'conversion',
        'subscription_amount', 'commission_rate', 'amount_earned',
        'month_year', 'billing_period_start', 'billing_period_end',
        'created_at', 'updated_at', 'net_amount'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Commission Details', {
            'fields': (
                'affiliate', 'referred_user_subscription', 'conversion',
                'subscription_amount', 'commission_rate', 'amount_earned'
            )
        }),
        ('Period Information', {
            'fields': ('month_year', 'billing_period_start', 'billing_period_end')
        }),
        ('Status & Payout', {
            'fields': (
                'status', 'paid_at', 'payout_method', 'payout_transaction_id',
                'payout_fee', 'net_amount'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def affiliate_code(self, obj):
        return obj.affiliate.referral_code
    affiliate_code.short_description = 'Affiliate Code'
    affiliate_code.admin_order_field = 'affiliate__referral_code'

    def status_display(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#17a2b8',
            'paid': '#28a745',
            'cancelled': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'affiliate', 'referred_user_subscription', 'conversion'
        )

    actions = ['approve_commissions', 'mark_as_paid']

    def approve_commissions(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f'Approved {updated} commission entries.')

    def mark_as_paid(self, request, queryset):
        for commission in queryset.filter(status='approved'):
            commission.mark_as_paid('manual', f'admin_payout_{commission.id}')
        self.message_user(request, f'Marked {queryset.count()} commissions as paid.')

    approve_commissions.short_description = "Approve selected commissions"
    mark_as_paid.short_description = "Mark selected commissions as paid"


@admin.register(AffiliateResource)
class AffiliateResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'resource_type', 'download_count', 'is_active', 'created_at'
    ]
    list_filter = ['resource_type', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'download_count', 'created_at']

    fieldsets = (
        ('Resource Information', {
            'fields': ('title', 'description', 'resource_type')
        }),
        ('Files & URLs', {
            'fields': ('file_url', 'thumbnail_url')
        }),
        ('Status & Statistics', {
            'fields': ('is_active', 'download_count', 'created_at')
        }),
    )