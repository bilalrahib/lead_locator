from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple
import logging

from apps.project_core.models import SubscriptionPlan, UserSubscription
from ..models import (
    LeadCreditPackage, PaymentHistory, UserLeadCredit,
    SubscriptionUpgradeRequest, SubscriptionCancellationRequest
)
from .payment_service import PaymentService

User = get_user_model()
logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscriptions."""

    def __init__(self):
        self.payment_service = PaymentService()

    @transaction.atomic
    def create_subscription(self, user: User, plan: SubscriptionPlan, 
                          payment_method_id: str = None) -> Tuple[UserSubscription, PaymentHistory]:
        """
        Create a new subscription for a user.
        
        Args:
            user: User instance
            plan: SubscriptionPlan instance
            payment_method_id: Stripe payment method ID
            
        Returns:
            Tuple of (UserSubscription, PaymentHistory)
        """
        # Check if user already has an active subscription
        if hasattr(user, 'subscription') and user.subscription and user.subscription.is_active:
            raise ValueError("User already has an active subscription")

        # Calculate billing dates
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)  # Monthly billing

        # Create payment record
        payment = PaymentHistory.objects.create(
            user=user,
            amount=plan.price,
            payment_gateway='stripe' if payment_method_id else 'manual',
            transaction_id=f"sub_{user.id}_{int(start_date.timestamp())}",
            status='pending'
        )

        try:
            # Process payment if not free
            if plan.price > 0:
                if not payment_method_id:
                    raise ValueError("Payment method required for paid plans")
                
                stripe_subscription = self.payment_service.create_stripe_subscription(
                    user=user,
                    plan=plan,
                    payment_method_id=payment_method_id
                )
                
                payment.gateway_transaction_id = stripe_subscription.id
                payment.mark_completed()
                stripe_subscription_id = stripe_subscription.id
            else:
                # Free plan
                payment.mark_completed()
                stripe_subscription_id = None

            # Create subscription
            subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                start_date=start_date,
                end_date=end_date,
                is_active=True,
                stripe_subscription_id=stripe_subscription_id
            )
            
            # Link payment to subscription
            payment.subscription = subscription
            payment.save()

            # Update user's current subscription
            user.current_subscription = subscription
            user.save(update_fields=['current_subscription'])

            logger.info(f"Created subscription for {user.email}: {plan.name}")
            return subscription, payment

        except Exception as e:
            payment.mark_failed(str(e))
            logger.error(f"Failed to create subscription for {user.email}: {e}")
            raise

    @transaction.atomic
    def upgrade_subscription(self, user: User, new_plan: SubscriptionPlan, 
                           effective_immediately: bool = True) -> SubscriptionUpgradeRequest:
        """
        Request subscription upgrade/downgrade.
        
        Args:
            user: User instance
            new_plan: New SubscriptionPlan
            effective_immediately: Whether to apply change immediately
            
        Returns:
            SubscriptionUpgradeRequest instance
        """
        current_subscription = user.subscription
        if not current_subscription or not current_subscription.is_active:
            raise ValueError("No active subscription found")

        if current_subscription.plan.id == new_plan.id:
            raise ValueError("Cannot change to the same plan")

        # Calculate proration
        proration_amount = self._calculate_proration(
            current_subscription, new_plan, effective_immediately
        )

        # Create upgrade request
        upgrade_request = SubscriptionUpgradeRequest.objects.create(
            user=user,
            current_subscription=current_subscription,
            requested_plan=new_plan,
            proration_amount=proration_amount,
            effective_date=timezone.now() if effective_immediately else current_subscription.end_date,
            status='approved'  # Auto-approve for now
        )

        if effective_immediately:
            self._process_upgrade_request(upgrade_request)

        logger.info(f"Created upgrade request for {user.email}: {current_subscription.plan.name} to {new_plan.name}")
        return upgrade_request

    @transaction.atomic
    def cancel_subscription(self, user: User, reason: str, feedback: str = "", 
                          cancel_immediately: bool = False) -> SubscriptionCancellationRequest:
        """
        Cancel user subscription.
        
        Args:
            user: User instance
            reason: Cancellation reason
            feedback: Additional feedback
            cancel_immediately: Whether to cancel immediately
            
        Returns:
            SubscriptionCancellationRequest instance
        """
        subscription = user.subscription
        if not subscription or not subscription.is_active:
            raise ValueError("No active subscription found")

        # Create cancellation request
        cancellation_request = SubscriptionCancellationRequest.objects.create(
            user=user,
            subscription=subscription,
            reason=reason,
            feedback=feedback,
            cancel_immediately=cancel_immediately,
            cancellation_date=timezone.now() if cancel_immediately else subscription.end_date
        )

        # Process cancellation
        if cancel_immediately:
            self._process_cancellation_immediately(subscription)
        else:
            # Cancel at end of billing period
            if subscription.stripe_subscription_id:
                self.payment_service.cancel_stripe_subscription(
                    subscription.stripe_subscription_id,
                    at_period_end=True
                )

        cancellation_request.is_processed = True
        cancellation_request.save()

        logger.info(f"Processed cancellation for {user.email}: {subscription.plan.name}")
        return cancellation_request

    def purchase_lead_credits(self, user: User, package: LeadCreditPackage, 
                            payment_method_id: str) -> Tuple[UserLeadCredit, PaymentHistory]:
        """
        Purchase additional lead credits.
        
        Args:
            user: User instance
            package: LeadCreditPackage instance
            payment_method_id: Stripe payment method ID
            
        Returns:
            Tuple of (UserLeadCredit, PaymentHistory)
        """
        # Create payment record
        payment = PaymentHistory.objects.create(
            user=user,
            package_purchased=package,
            amount=package.price,
            payment_gateway='stripe',
            transaction_id=f"pkg_{user.id}_{int(timezone.now().timestamp())}",
            status='pending'
        )

        try:
            # Process payment
            stripe_payment = self.payment_service.process_one_time_payment(
                user=user,
                amount=package.price,
                payment_method_id=payment_method_id,
                description=f"Lead Credit Package: {package.name}"
            )
            
            payment.gateway_transaction_id = stripe_payment.id
            payment.mark_completed()

            # Create lead credit record
            lead_credit = UserLeadCredit.objects.create(
                user=user,
                package=package,
                payment=payment,
                credits_purchased=package.lead_count,
                expires_at=timezone.now() + timedelta(days=365)  # Credits expire in 1 year
            )

            logger.info(f"Purchased lead credits for {user.email}: {package.name}")
            return lead_credit, payment

        except Exception as e:
            payment.mark_failed(str(e))
            logger.error(f"Failed to purchase lead credits for {user.email}: {e}")
            raise

    def get_user_usage_stats(self, user: User) -> Dict:
        """
        Get user's subscription usage statistics.
        
        Args:
            user: User instance
            
        Returns:
            Dict with usage statistics
        """
        if not hasattr(user, 'subscription') or not user.subscription or not user.subscription.is_active:
            return {
                'current_plan': 'None',
                'searches_used': 0,
                'searches_limit': 0,
                'searches_remaining': 0,
                'additional_credits': 0,
                'billing_period_start': None,
                'billing_period_end': None,
                'next_reset_date': None,
            }

        subscription = user.subscription
        
        # Get additional credits
        from django.db.models import Sum
        additional_credits = UserLeadCredit.objects.filter(
            user=user,
            expires_at__gte=timezone.now()
        ).aggregate(
            total=Sum('credits_purchased') - Sum('credits_used')
        )['total'] or 0

        return {
            'current_plan': subscription.plan.name,
            'searches_used': subscription.searches_used_this_period,
            'searches_limit': subscription.plan.leads_per_month,
            'searches_remaining': subscription.searches_left_this_period(),
            'additional_credits': additional_credits,
            'billing_period_start': subscription.start_date,
            'billing_period_end': subscription.end_date,
            'next_reset_date': subscription.end_date,
        }

    def reset_monthly_usage(self, subscription: UserSubscription):
        """
        Reset monthly usage counters for a subscription.
        
        Args:
            subscription: UserSubscription instance
        """
        subscription.searches_used_this_period = 0
        subscription.start_date = timezone.now()
        subscription.end_date = subscription.start_date + timedelta(days=30)
        subscription.save(update_fields=[
            'searches_used_this_period', 'start_date', 'end_date'
        ])
        
        logger.info(f"Reset monthly usage for subscription {subscription.id}")

    def _calculate_proration(self, current_subscription: UserSubscription, 
                           new_plan: SubscriptionPlan, immediate: bool) -> Optional[Decimal]:
        """Calculate proration amount for plan changes."""
        if not immediate:
            return None

        current_plan = current_subscription.plan
        days_remaining = (current_subscription.end_date - timezone.now()).days
        
        if days_remaining <= 0:
            return new_plan.price

        # Calculate prorated amounts
        daily_old_rate = current_plan.price / 30
        daily_new_rate = new_plan.price / 30
        
        old_amount_remaining = daily_old_rate * days_remaining
        new_amount_for_period = daily_new_rate * days_remaining
        
        return new_amount_for_period - old_amount_remaining

    @transaction.atomic
    def _process_upgrade_request(self, upgrade_request: SubscriptionUpgradeRequest):
        """Process an approved upgrade request."""
        subscription = upgrade_request.current_subscription
        new_plan = upgrade_request.requested_plan

        # Update subscription
        subscription.plan = new_plan
        
        # If there's a proration charge, process it
        if upgrade_request.proration_amount and upgrade_request.proration_amount > 0:
            # Create payment for proration
            payment = PaymentHistory.objects.create(
                user=upgrade_request.user,
                subscription=subscription,
                amount=upgrade_request.proration_amount,
                payment_gateway='stripe',
                transaction_id=f"proration_{subscription.id}_{int(timezone.now().timestamp())}",
                status='completed'  # For now, assume successful
            )

        subscription.save()
        upgrade_request.status = 'completed'
        upgrade_request.save()

        # Update user's current subscription reference
        subscription.user.current_subscription = subscription
        subscription.user.save(update_fields=['current_subscription'])

    def _process_cancellation_immediately(self, subscription: UserSubscription):
        """Process immediate cancellation."""
        subscription.is_active = False
        subscription.end_date = timezone.now()
        subscription.save()

        # Cancel Stripe subscription if exists
        if subscription.stripe_subscription_id:
            self.payment_service.cancel_stripe_subscription(
                subscription.stripe_subscription_id,
                at_period_end=False
            )

        # Update user reference
        subscription.user.current_subscription = None
        subscription.user.save(update_fields=['current_subscription'])