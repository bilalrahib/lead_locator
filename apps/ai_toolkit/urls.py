# apps/ai_toolkit/urls.py
from django.urls import path, include
from .views import (
    GeneratedScriptListAPIView, ScriptGenerationAPIView, ScriptRegenerationAPIView,
    ScriptTemplateListAPIView, TemplateUsageAPIView, JarvisChatAPIView,
    JarvisConversationHistoryAPIView, LogoGenerationAPIView, SocialMediaGenerationAPIView,
    LeadValueCalculationAPIView, SnackPriceCalculationAPIView, BusinessCalculationHistoryAPIView,
    BusinessCalculationDetailAPIView
)

app_name = 'ai_toolkit'

# Script Generation URLs
script_patterns = [
    path('', GeneratedScriptListAPIView.as_view(), name='script-list'),
    path('generate/', ScriptGenerationAPIView.as_view(), name='script-generate'),
    path('regenerate/', ScriptRegenerationAPIView.as_view(), name='script-regenerate'),
    path('templates/', ScriptTemplateListAPIView.as_view(), name='script-templates'),
    path('templates/use/', TemplateUsageAPIView.as_view(), name='template-use'),
]

# JARVIS AI Assistant URLs
jarvis_patterns = [
    path('chat/', JarvisChatAPIView.as_view(), name='jarvis-chat'),
    path('conversations/', JarvisConversationHistoryAPIView.as_view(), name='jarvis-history'),
    path('logo-generation/', LogoGenerationAPIView.as_view(), name='jarvis-logo'),
    path('social-media/', SocialMediaGenerationAPIView.as_view(), name='jarvis-social'),
]

# Business Tools URLs
business_tools_patterns = [
    path('lead-value-calculator/', LeadValueCalculationAPIView.as_view(), name='lead-value-calculator'),
    path('snack-price-calculator/', SnackPriceCalculationAPIView.as_view(), name='snack-price-calculator'),
    path('calculations/', BusinessCalculationHistoryAPIView.as_view(), name='calculation-history'),
    path('calculations/<uuid:calculation_id>/', BusinessCalculationDetailAPIView.as_view(), name='calculation-detail'),
]

urlpatterns = [
    path('api/v1/ai-toolkit/scripts/', include(script_patterns)),
    path('api/v1/ai-toolkit/jarvis/', include(jarvis_patterns)),
    path('api/v1/ai-toolkit/business-tools/', include(business_tools_patterns)),
]