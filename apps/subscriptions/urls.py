from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # Subscription Plans
    path('api/v1/subscriptions/plans/', views.SubscriptionPlansListAPIView.as_view(), name='plans'),
    path('api/v1/subscriptions/packages/', views.LeadCreditPackagesListAPIView.as_view(), name='packages'),
    
    # Current Subscription
    path('api/v1/subscriptions/current/', views.CurrentSubscriptionAPIView.as_view(), name='current'),
    path('api/v1/subscriptions/subscribe/', views.SubscriptionCreateAPIView.as_view(), name='subscribe'),
    path('api/v1/subscriptions/upgrade/', views.SubscriptionUpgradeAPIView.as_view(), name='upgrade'),
    path('api/v1/subscriptions/cancel/', views.SubscriptionCancelAPIView.as_view(), name='cancel'),
    
    # Package Purchases
    path('api/v1/subscriptions/purchase-package/', views.PackagePurchaseAPIView.as_view(), name='purchase_package'),
    
    # Usage and Billing
    path('api/v1/subscriptions/usage/', views.UsageStatsAPIView.as_view(), name='usage'),
    path('api/v1/subscriptions/payment-history/', views.PaymentHistoryAPIView.as_view(), name='payment_history'),
    path('api/v1/subscriptions/billing-history/', views.BillingHistoryAPIView.as_view(), name='billing_history'),
    path('api/v1/subscriptions/lead-credits/', views.UserLeadCreditsAPIView.as_view(), name='lead_credits'),
    path('api/v1/subscriptions/payment-methods/', views.PaymentMethodsAPIView.as_view(), name='payment_methods'),
    
    # Webhooks
    path('api/v1/webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),
    
    # Health Check
    path('api/v1/subscriptions/health/', views.subscription_health_check, name='health'),
]