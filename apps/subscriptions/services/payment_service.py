import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from typing import Dict, Optional
import logging

from apps.project_core.models import SubscriptionPlan

User = get_user_model()
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class PaymentService:
    """Service for handling payments through Stripe and PayPal."""

    def __init__(self):
        self.stripe_api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        self.stripe_publishable_key = getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')

    def create_or_get_stripe_customer(self, user: User) -> stripe.Customer:
        """
        Create or retrieve Stripe customer for user.
        
        Args:
            user: User instance
            
        Returns:
            Stripe Customer object
        """
        # For now, always create a new customer
        # In production, you'd store customer_id on the user model
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={
                'user_id': str(user.id),
                'username': user.username
            }
        )

        logger.info(f"Created Stripe customer for {user.email}: {customer.id}")
        return customer

    def create_stripe_subscription(self, user: User, plan: SubscriptionPlan, 
                                 payment_method_id: str) -> stripe.Subscription:
        """
        Create Stripe subscription.
        
        Args:
            user: User instance
            plan: SubscriptionPlan instance
            payment_method_id: Stripe payment method ID
            
        Returns:
            Stripe Subscription object
        """
        try:
            # Get or create customer
            customer = self.create_or_get_stripe_customer(user)

            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )

            # Set as default payment method
            stripe.Customer.modify(
                customer.id,
                invoice_settings={
                    'default_payment_method': payment_method_id,
                },
            )

            # Create or get price object for the plan
            price = self._get_or_create_stripe_price(plan)

            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price.id}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
                metadata={
                    'plan_id': str(plan.id),
                    'plan_name': plan.name,
                    'user_id': str(user.id)
                }
            )

            logger.info(f"Created Stripe subscription for {user.email}: {subscription.id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription for {user.email}: {e}")
            raise Exception(f"Payment failed: {str(e)}")

    def cancel_stripe_subscription(self, subscription_id: str, at_period_end: bool = True):
        """
        Cancel Stripe subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            at_period_end: Whether to cancel at period end or immediately
        """
        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=at_period_end
            )
            
            if not at_period_end:
                stripe.Subscription.delete(subscription_id)

            logger.info(f"Cancelled Stripe subscription: {subscription_id}")

        except stripe.error.StripeError as e:
            logger.error(f"Error cancelling Stripe subscription {subscription_id}: {e}")
            raise

    def process_one_time_payment(self, user: User, amount: float, 
                                payment_method_id: str, description: str) -> stripe.PaymentIntent:
        """
        Process one-time payment.
        
        Args:
            user: User instance
            amount: Payment amount
            payment_method_id: Stripe payment method ID
            description: Payment description
            
        Returns:
            Stripe PaymentIntent object
        """
        try:
            # Get or create customer
            customer = self.create_or_get_stripe_customer(user)

            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                customer=customer.id,
                payment_method=payment_method_id,
                description=description,
                confirm=True,
                metadata={
                    'user_id': str(user.id),
                    'type': 'one_time_purchase'
                }
            )

            logger.info(f"Processed one-time payment for {user.email}: ${amount}")
            return intent

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error processing payment for {user.email}: {e}")
            raise Exception(f"Payment failed: {str(e)}")

    def create_setup_intent(self, user: User) -> stripe.SetupIntent:
        """
        Create setup intent for saving payment methods.
        
        Args:
            user: User instance
            
        Returns:
            Stripe SetupIntent object
        """
        try:
            customer = self.create_or_get_stripe_customer(user)
            
            setup_intent = stripe.SetupIntent.create(
                customer=customer.id,
                usage='off_session'
            )

            return setup_intent

        except stripe.error.StripeError as e:
            logger.error(f"Error creating setup intent for {user.email}: {e}")
            raise

    def get_customer_payment_methods(self, user: User) -> list:
        """
        Get customer's saved payment methods.
        
        Args:
            user: User instance
            
        Returns:
            List of payment methods
        """
        try:
            customer = self.create_or_get_stripe_customer(user)
            
            payment_methods = stripe.PaymentMethod.list(
                customer=customer.id,
                type='card'
            )

            return payment_methods.data

        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving payment methods for {user.email}: {e}")
            return []

    def _get_or_create_stripe_price(self, plan: SubscriptionPlan) -> stripe.Price:
        """Get or create Stripe price for subscription plan."""
        # For simplicity, always create a new price
        # In production, you'd cache/store price IDs
        
        # Create new product
        product = stripe.Product.create(
           name=f"Vending Hive - {plan.get_name_display()}",
           description=plan.description,
           metadata={
               'plan_id': str(plan.id),
               'plan_name': plan.name
           }
        )

        price = stripe.Price.create(
           unit_amount=int(plan.price * 100),  # Convert to cents
           currency='usd',
           recurring={'interval': 'month'},
           product=product.id,
           metadata={
               'plan_id': str(plan.id),
               'plan_name': plan.name
           }
        )

        logger.info(f"Created Stripe price for plan {plan.name}: {price.id}")
        return price

    def handle_webhook_event(self, event_type: str, event_data: Dict) -> bool:
       
       """
       Handle Stripe webhook events.
       
       Args:
           event_type: Stripe event type
           event_data: Event data
           
       Returns:
           Boolean indicating success
       """
       try:
           if event_type == 'invoice.payment_succeeded':
               return self._handle_payment_succeeded(event_data)
           elif event_type == 'invoice.payment_failed':
               return self._handle_payment_failed(event_data)
           elif event_type == 'customer.subscription.updated':
               return self._handle_subscription_updated(event_data)
           elif event_type == 'customer.subscription.deleted':
               return self._handle_subscription_deleted(event_data)
           else:
               logger.info(f"Unhandled webhook event type: {event_type}")
               return True

       except Exception as e:
           logger.error(f"Error handling webhook event {event_type}: {e}")
           return False

    def _handle_payment_succeeded(self, event_data: Dict) -> bool:
       """Handle successful payment webhook."""
       subscription_id = event_data.get('subscription')
       if not subscription_id:
           return True

       try:
           from apps.project_core.models import UserSubscription
           subscription = UserSubscription.objects.get(
               stripe_subscription_id=subscription_id
           )
           
           # Reset monthly usage if this is a recurring payment
           from .subscription_service import SubscriptionService
           service = SubscriptionService()
           service.reset_monthly_usage(subscription)
           
           logger.info(f"Processed payment success for subscription {subscription_id}")
           return True

       except UserSubscription.DoesNotExist:
           logger.warning(f"Subscription not found for Stripe ID: {subscription_id}")
           return True

    def _handle_payment_failed(self, event_data: Dict) -> bool:
       """Handle failed payment webhook."""
       subscription_id = event_data.get('subscription')
       if not subscription_id:
           return True

       try:
           from apps.project_core.models import UserSubscription
           subscription = UserSubscription.objects.get(
               stripe_subscription_id=subscription_id
           )
           
           # You might want to send an email or take other action
           logger.warning(f"Payment failed for subscription {subscription_id}")
           return True

       except UserSubscription.DoesNotExist:
           logger.warning(f"Subscription not found for Stripe ID: {subscription_id}")
           return True

    def _handle_subscription_updated(self, event_data: Dict) -> bool:
       """Handle subscription updated webhook."""
       # Handle subscription updates
       logger.info("Subscription updated webhook received")
       return True

    def _handle_subscription_deleted(self, event_data: Dict) -> bool:
       """Handle subscription deleted webhook."""
       subscription_id = event_data.get('id')
       
       try:
           from apps.project_core.models import UserSubscription
           subscription = UserSubscription.objects.get(
               stripe_subscription_id=subscription_id
           )
           
           subscription.is_active = False
           subscription.end_date = timezone.now()
           subscription.save()
           
           # Update user reference
           subscription.user.current_subscription = None
           subscription.user.save(update_fields=['current_subscription'])
           
           logger.info(f"Processed subscription deletion for {subscription_id}")
           return True

       except UserSubscription.DoesNotExist:
           logger.warning(f"Subscription not found for Stripe ID: {subscription_id}")
           return True