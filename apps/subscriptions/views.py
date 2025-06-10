from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Count, Q
from django.utils import timezone
import json
import stripe
import logging

from apps.project_core.models import SubscriptionPlan, UserSubscription
from .models import (
    LeadCreditPackage, PaymentHistory, UserLeadCredit,
    SubscriptionUpgradeRequest, SubscriptionCancellationRequest
)
from .serializers import (
    SubscriptionPlanDetailSerializer, LeadCreditPackageSerializer,
    UserSubscriptionDetailSerializer, PaymentHistorySerializer,
    UserLeadCreditSerializer, SubscriptionCreateSerializer,
    PackagePurchaseSerializer, SubscriptionUpgradeSerializer,
    SubscriptionCancellationSerializer, UsageStatsSerializer,
    BillingHistorySerializer
)
from .services import SubscriptionService, PaymentService

logger = logging.getLogger(__name__)


class SubscriptionPlansListAPIView(generics.ListAPIView):
    """
    API endpoint for listing subscription plans.
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanDetailSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by('price')


class LeadCreditPackagesListAPIView(generics.ListAPIView):
    """
    API endpoint for listing lead credit packages.
    """
    queryset = LeadCreditPackage.objects.filter(is_active=True)
    serializer_class = LeadCreditPackageSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by target plan if specified
        target_plan = self.request.query_params.get('target_plan')
        if target_plan:
            queryset = queryset.filter(
                Q(target_buyer_plan__name=target_plan) | Q(target_buyer_plan__isnull=True)
            )
        
        return queryset.order_by('price')


class CurrentSubscriptionAPIView(APIView):
    """
    API endpoint for current user subscription details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current subscription details."""
        user = request.user
        
        if not hasattr(user, 'subscription') or not user.subscription:
            return Response({
                'subscription': None,
                'message': 'No active subscription found'
            })

        serializer = UserSubscriptionDetailSerializer(user.subscription)
        return Response({'subscription': serializer.data})


class SubscriptionCreateAPIView(APIView):
    """
    API endpoint for creating new subscriptions.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create new subscription."""
        serializer = SubscriptionCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = SubscriptionPlan.objects.get(
                id=serializer.validated_data['plan_id'],
                is_active=True
            )
            
            subscription_service = SubscriptionService()
            subscription, payment = subscription_service.create_subscription(
                user=request.user,
                plan=plan,
                payment_method_id=serializer.validated_data.get('payment_method_id')
            )

            subscription_data = UserSubscriptionDetailSerializer(subscription).data
            
            return Response({
                'subscription': subscription_data,
                'payment': {
                    'id': str(payment.id),
                    'amount': payment.amount,
                    'status': payment.status
                },
                'message': 'Subscription created successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating subscription for {request.user.email}: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionUpgradeAPIView(APIView):
    """
    API endpoint for subscription upgrades/downgrades.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Upgrade/downgrade subscription."""
        serializer = SubscriptionUpgradeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_plan = SubscriptionPlan.objects.get(
                id=serializer.validated_data['new_plan_id']
            )
            
            subscription_service = SubscriptionService()
            upgrade_request = subscription_service.upgrade_subscription(
                user=request.user,
                new_plan=new_plan,
                effective_immediately=serializer.validated_data['effective_immediately']
            )

            return Response({
                'upgrade_request': {
                    'id': str(upgrade_request.id),
                    'status': upgrade_request.status,
                    'proration_amount': upgrade_request.proration_amount,
                    'effective_date': upgrade_request.effective_date
                },
                'message': 'Subscription upgrade processed successfully'
            })

        except Exception as e:
            logger.error(f"Error upgrading subscription for {request.user.email}: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionCancelAPIView(APIView):
    """
    API endpoint for subscription cancellation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Cancel subscription."""
        serializer = SubscriptionCancellationSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            subscription_service = SubscriptionService()
            cancellation_request = subscription_service.cancel_subscription(
                user=request.user,
                reason=serializer.validated_data['reason'],
                feedback=serializer.validated_data.get('feedback', ''),
                cancel_immediately=serializer.validated_data.get('cancel_immediately', False)
            )

            return Response({
                'cancellation_request': {
                    'id': str(cancellation_request.id),
                    'cancellation_date': cancellation_request.cancellation_date,
                    'is_processed': cancellation_request.is_processed
                },
                'message': 'Subscription cancellation processed successfully'
            })

        except Exception as e:
            logger.error(f"Error cancelling subscription for {request.user.email}: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PackagePurchaseAPIView(APIView):
    """
    API endpoint for purchasing lead credit packages.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Purchase lead credit package."""
        serializer = PackagePurchaseSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            package = LeadCreditPackage.objects.get(
                id=serializer.validated_data['package_id'],
                is_active=True
            )
            
            subscription_service = SubscriptionService()
            lead_credit, payment = subscription_service.purchase_lead_credits(
                user=request.user,
                package=package,
                payment_method_id=serializer.validated_data['payment_method_id']
            )

            return Response({
                'lead_credit': UserLeadCreditSerializer(lead_credit).data,
                'payment': {
                    'id': str(payment.id),
                    'amount': payment.amount,
                    'status': payment.status
                },
                'message': 'Lead credit package purchased successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error purchasing package for {request.user.email}: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UsageStatsAPIView(APIView):
    """
    API endpoint for subscription usage statistics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get usage statistics."""
        subscription_service = SubscriptionService()
        stats = subscription_service.get_user_usage_stats(request.user)
        
        serializer = UsageStatsSerializer(stats)
        return Response(serializer.data)


class PaymentHistoryAPIView(generics.ListAPIView):
    """
    API endpoint for user payment history.
    """
    serializer_class = PaymentHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PaymentHistory.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class BillingHistoryAPIView(APIView):
    """
    API endpoint for billing history summary.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get billing history summary."""
        user = request.user
        payments = PaymentHistory.objects.filter(user=user).order_by('-created_at')
        
        # Calculate totals
        total_spent = payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        subscription_payments = payments.filter(
            subscription__isnull=False,
            status='completed'
        ).count()
        
        package_purchases = payments.filter(
            package_purchased__isnull=False,
            status='completed'
        ).count()

        serializer = BillingHistorySerializer({
            'payments': payments,
            'total_spent': total_spent,
            'subscription_payments': subscription_payments,
            'package_purchases': package_purchases
        })
        
        return Response(serializer.data)


class UserLeadCreditsAPIView(generics.ListAPIView):
    """
    API endpoint for user's lead credits.
    """
    serializer_class = UserLeadCreditSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserLeadCredit.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class PaymentMethodsAPIView(APIView):
    """
    API endpoint for managing payment methods.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's saved payment methods."""
        payment_service = PaymentService()
        payment_methods = payment_service.get_customer_payment_methods(request.user)
        
        return Response({
            'payment_methods': payment_methods
        })

    def post(self, request):
        """Create setup intent for adding payment method."""
        payment_service = PaymentService()
        
        try:
            setup_intent = payment_service.create_setup_intent(request.user)
            
            return Response({
                'client_secret': setup_intent.client_secret
            })
            
        except Exception as e:
            logger.error(f"Error creating setup intent for {request.user.email}: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# Webhook Views
@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook endpoint.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid payload in Stripe webhook")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in Stripe webhook")
        return HttpResponse(status=400)

    # Handle the event
    payment_service = PaymentService()
    success = payment_service.handle_webhook_event(
        event['type'],
        event['data']['object']
    )

    if success:
        logger.info(f"Processed Stripe webhook event: {event['type']}")
        return HttpResponse(status=200)
    else:
        logger.error(f"Failed to process Stripe webhook event: {event['type']}")
        return HttpResponse(status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def subscription_health_check(request):
    """
    Health check for subscriptions app.
    """
    try:
        # Test database connections
        plans_count = SubscriptionPlan.objects.count()
        packages_count = LeadCreditPackage.objects.count()
        
        return Response({
            'status': 'healthy',
            'subscription_plans': plans_count,
            'lead_packages': packages_count,
            'app': 'subscriptions'
        })
        
    except Exception as e:
        logger.error(f"Subscriptions health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'app': 'subscriptions'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)