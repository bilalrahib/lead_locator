from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import GeneratedScript, ScriptTemplate, JarvisConversation, BusinessCalculation


@admin.register(GeneratedScript)
class GeneratedScriptAdmin(admin.ModelAdmin):
    """Admin interface for Generated Scripts."""
    
    list_display = [
        'id', 'user_email', 'script_type', 'target_location_name', 
        'target_machine_type', 'is_template', 'regeneration_count', 
        'ai_model_used', 'created_at'
    ]
    list_filter = [
        'script_type', 'target_machine_type', 'is_template', 
        'ai_model_used', 'created_at'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'target_location_name', 'target_location_category'
    ]
    readonly_fields = [
        'id', 'user', 'regeneration_count', 'ai_model_used', 
        'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Script Information', {
            'fields': ('id', 'user', 'script_type', 'is_template')
        }),
        ('Target Details', {
            'fields': (
                'target_location_name', 'target_location_category', 
                'target_machine_type'
            )
        }),
        ('Content', {
            'fields': ('script_content',),
            'classes': ('wide',)
        }),
        ('AI Information', {
            'fields': ('ai_model_used', 'regeneration_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def user_email(self, obj):
        """Display user email with link to user admin."""
        if obj.user:
            url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')


@admin.register(ScriptTemplate)
class ScriptTemplateAdmin(admin.ModelAdmin):
    """Admin interface for Script Templates."""
    
    list_display = [
        'name', 'script_type', 'machine_type', 'location_category',
        'is_premium', 'is_active', 'usage_count', 'created_at'
    ]
    list_filter = [
        'script_type', 'machine_type', 'is_premium', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'location_category', 'content']
    readonly_fields = ['id', 'usage_count', 'created_at', 'updated_at']
    fieldsets = (
        ('Template Information', {
            'fields': ('id', 'name', 'script_type', 'machine_type', 'location_category')
        }),
        ('Access Control', {
            'fields': ('is_premium', 'is_active')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Statistics', {
            'fields': ('usage_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    date_hierarchy = 'created_at'
    ordering = ['script_type', 'name']
    
    def save_model(self, request, obj, form, change):
        """Save template with validation."""
        super().save_model(request, obj, form, change)


@admin.register(JarvisConversation)
class JarvisConversationAdmin(admin.ModelAdmin):
    """Admin interface for JARVIS Conversations."""
    
    list_display = [
        'id', 'user_email', 'conversation_type', 'session_id_short',
        'message_preview', 'ai_model_used', 'response_time_ms', 'created_at'
    ]
    list_filter = [
        'conversation_type', 'ai_model_used', 'created_at'
    ]
    search_fields = [
        'user__email', 'user_message', 'jarvis_response', 'session_id'
    ]
    readonly_fields = [
        'id', 'user', 'session_id', 'user_message', 'jarvis_response',
        'conversation_type', 'ai_model_used', 'response_time_ms', 'created_at'
    ]
    fieldsets = (
        ('Conversation Information', {
            'fields': ('id', 'user', 'session_id', 'conversation_type')
        }),
        ('Messages', {
            'fields': ('user_message', 'jarvis_response'),
            'classes': ('wide',)
        }),
        ('AI Information', {
            'fields': ('ai_model_used', 'response_time_ms'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def user_email(self, obj):
        """Display user email with link."""
        if obj.user:
            url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def session_id_short(self, obj):
        """Display shortened session ID."""
        return obj.session_id[:8] + '...' if len(obj.session_id) > 8 else obj.session_id
    session_id_short.short_description = 'Session'
    
    def message_preview(self, obj):
        """Display message preview."""
        return obj.user_message[:50] + '...' if len(obj.user_message) > 50 else obj.user_message
    message_preview.short_description = 'Message Preview'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user')


@admin.register(BusinessCalculation)
class BusinessCalculationAdmin(admin.ModelAdmin):
    """Admin interface for Business Calculations."""
    
    list_display = [
        'id', 'user_email', 'calculation_type', 'calculation_preview',
        'created_at'
    ]
    list_filter = ['calculation_type', 'created_at']
    search_fields = ['user__email', 'notes']
    readonly_fields = [
        'id', 'user', 'calculation_type', 'input_parameters',
        'calculation_results', 'created_at'
    ]
    fieldsets = (
        ('Calculation Information', {
            'fields': ('id', 'user', 'calculation_type')
        }),
        ('Data', {
            'fields': ('input_parameters', 'calculation_results'),
            'classes': ('wide', 'collapse')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def user_email(self, obj):
        """Display user email with link."""
        if obj.user:
            url = reverse('admin:accounts_customuser_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def calculation_preview(self, obj):
        """Display calculation preview."""
        if obj.calculation_type == 'lead_value_estimator':
            goal = obj.input_parameters.get('business_goals', {}).get('monthly_revenue_goal', 'N/A')
            return f"Goal: ${goal}"
        elif obj.calculation_type == 'snack_price_calculator':
            price = obj.input_parameters.get('pricing_strategy', {}).get('sale_price', 'N/A')
            return f"Price: ${price}"
        return 'N/A'
    calculation_preview.short_description = 'Preview'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user')


# Custom admin site configurations
admin.site.site_header = "Vending Hive AI Toolkit Administration"
admin.site.site_title = "AI Toolkit Admin"
admin.site.index_title = "AI Toolkit Management"