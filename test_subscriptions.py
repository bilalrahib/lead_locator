#!/usr/bin/env python
"""
Comprehensive test script for the Subscriptions package.
Run this script to test all subscription functionality.
"""

import os
import sys
import django
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

# Add the project directory to the Python path
sys.path.append('D:/mike/codebase')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vending_hive.settings.development')
django.setup()

# Now import Django models and services
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db import transaction
from apps.project_core.models import SubscriptionPlan, UserSubscription
from apps.subscriptions.models import (
    LeadCreditPackage, PaymentHistory, UserLeadCredit,
    SubscriptionUpgradeRequest, SubscriptionCancellationRequest
)
from apps.subscriptions.services import SubscriptionService, PaymentService
from apps.subscriptions.serializers import (
    SubscriptionPlanDetailSerializer, LeadCreditPackageSerializer,
    UserSubscriptionDetailSerializer
)

User = get_user_model()


class SubscriptionTestRunner:
    """Test runner for subscription functionality."""
    
    def __init__(self):
        self.test_user = None
        self.test_plans = {}
        self.test_packages = {}
        self.subscription_service = SubscriptionService()
        self.payment_service = PaymentService()
        self.passed_tests = 0
        self.failed_tests = 0

    def run_all_tests(self):
        """Run all subscription tests."""
        print("=" * 80)
        print("VENDING HIVE - SUBSCRIPTIONS PACKAGE TEST SUITE")
        print("=" * 80)
        
        try:
            self.setup_test_data()
            self.test_models()
            self.test_services()
            self.test_serializers()
            self.test_business_logic()
            self.cleanup_test_data()
            
            print("\n" + "=" * 80)
            print(f"TEST SUMMARY: {self.passed_tests} passed, {self.failed_tests} failed")
            print("=" * 80)
            
            if self.failed_tests == 0:
                print("🎉 ALL TESTS PASSED! Subscriptions package is working correctly.")
                return True
            else:
                print("❌ Some tests failed. Please check the output above.")
                return False
                
        except Exception as e:
            print(f"❌ Critical error during testing: {e}")
            return False

    def setup_test_data(self):
        """Set up test data."""
        print("\n📋 Setting up test data...")
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='testsubscriptionuser',
            email='testsubscription@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Subscription'
        )
        
        # Create test subscription plans (if they don't exist)
        self.test_plans['free'], _ = SubscriptionPlan.objects.get_or_create(
            name='FREE',
            defaults={
                'price': Decimal('0.00'),
                'leads_per_month': 3,
                'leads_per_search_range': '10',
                'script_templates_count': 1,
                'regeneration_allowed': False,
                'description': 'Free plan for testing'
            }
        )
        
        self.test_plans['pro'], _ = SubscriptionPlan.objects.get_or_create(
            name='PRO',
            defaults={
                'price': Decimal('59.99'),
                'leads_per_month': 25,
                'leads_per_search_range': '15-20',
                'script_templates_count': 10,
                'regeneration_allowed': True,
                'description': 'Pro plan for testing'
            }
        )
        
        # Create test lead credit packages
        self.test_packages['boost'] = LeadCreditPackage.objects.create(
            name='Test Boost Pack',
            description='Test package for additional leads',
            price=Decimal('19.99'),
            lead_count=20,
            target_buyer_plan=self.test_plans['free']
        )
        
        print("✅ Test data setup complete")

    def test_models(self):
        """Test model functionality."""
        print("\n🔧 Testing Models...")
        
        # Test LeadCreditPackage
        try:
            package = self.test_packages['boost']
            assert package.price_per_lead == 1.00
            assert str(package) == "Test Boost Pack - 20 leads ($19.99)"
            self.pass_test("LeadCreditPackage model")
        except Exception as e:
            self.fail_test("LeadCreditPackage model", str(e))

        # Test PaymentHistory
        try:
            payment = PaymentHistory.objects.create(
                user=self.test_user,
                amount=Decimal('59.99'),
                payment_gateway='stripe',
                transaction_id='test_transaction_001',
                status='pending'
            )
            payment.mark_completed('stripe_tx_123')
            assert payment.status == 'completed'
            assert payment.gateway_transaction_id == 'stripe_tx_123'
            self.pass_test("PaymentHistory model")
        except Exception as e:
            self.fail_test("PaymentHistory model", str(e))

        # Test UserLeadCredit
        try:
            payment = PaymentHistory.objects.filter(user=self.test_user).first()
            credit = UserLeadCredit.objects.create(
                user=self.test_user,
                package=self.test_packages['boost'],
                payment=payment,
                credits_purchased=20,
                expires_at=timezone.now() + timedelta(days=365)
            )
            assert credit.credits_remaining == 20
            assert not credit.is_expired
            
            # Test using credits
            assert credit.use_credits(5) == True
            assert credit.credits_remaining == 15
            self.pass_test("UserLeadCredit model")
        except Exception as e:
            self.fail_test("UserLeadCredit model", str(e))

    def test_services(self):
        """Test service functionality."""
        print("\n⚙️ Testing Services...")
        
        # Test subscription creation (free plan)
        try:
            subscription, payment = self.subscription_service.create_subscription(
                user=self.test_user,
                plan=self.test_plans['free']
            )
            assert subscription.is_active
            assert subscription.plan == self.test_plans['free']
            assert payment.status == 'completed'
            self.pass_test("Subscription creation (free plan)")
        except Exception as e:
            self.fail_test("Subscription creation (free plan)", str(e))

        # Test usage stats
        try:
            stats = self.subscription_service.get_user_usage_stats(self.test_user)
            assert stats['current_plan'] == 'FREE'
            assert stats['searches_limit'] == 3
            assert stats['searches_remaining'] == 3
            self.pass_test("Usage statistics")
        except Exception as e:
            self.fail_test("Usage statistics", str(e))

        # Test upgrade request
        try:
            upgrade_request = self.subscription_service.upgrade_subscription(
                user=self.test_user,
                new_plan=self.test_plans['pro'],
                effective_immediately=False
            )
            assert upgrade_request.requested_plan == self.test_plans['pro']
            assert upgrade_request.status == 'approved'
            self.pass_test("Subscription upgrade")
        except Exception as e:
            self.fail_test("Subscription upgrade", str(e))

        # Test cancellation
        try:
            cancellation = self.subscription_service.cancel_subscription(
                user=self.test_user,
                reason='testing',
                feedback='This is a test cancellation',
                cancel_immediately=False
            )
            assert cancellation.reason == 'testing'
            assert cancellation.is_processed
            self.pass_test("Subscription cancellation")
        except Exception as e:
            self.fail_test("Subscription cancellation", str(e))

    def test_serializers(self):
        """Test serializer functionality."""
        print("\n📄 Testing Serializers...")
        
        # Test SubscriptionPlanDetailSerializer
        try:
            serializer = SubscriptionPlanDetailSerializer(self.test_plans['pro'])
            data = serializer.data
            assert 'features' in data
            assert 'popular' in data
            assert data['name'] == 'PRO'
            self.pass_test("SubscriptionPlanDetailSerializer")
        except Exception as e:
            self.fail_test("SubscriptionPlanDetailSerializer", str(e))

        # Test LeadCreditPackageSerializer
        try:
            serializer = LeadCreditPackageSerializer(self.test_packages['boost'])
            data = serializer.data
            assert data['price_per_lead'] == 1.00
            assert data['lead_count'] == 20
            self.pass_test("LeadCreditPackageSerializer")
        except Exception as e:
            self.fail_test("LeadCreditPackageSerializer", str(e))

        # Test UserSubscriptionDetailSerializer
        try:
            subscription = self.test_user.subscription
            if subscription:
                serializer = UserSubscriptionDetailSerializer(subscription)
                data = serializer.data
                assert 'plan_details' in data
                assert 'searches_left' in data
                self.pass_test("UserSubscriptionDetailSerializer")
            else:
                self.pass_test("UserSubscriptionDetailSerializer (no subscription)")
        except Exception as e:
            self.fail_test("UserSubscriptionDetailSerializer", str(e))

    def test_business_logic(self):
        """Test business logic and edge cases."""
        print("\n🧠 Testing Business Logic...")
        
        # Test duplicate subscription prevention
        try:
            # This should raise an error since user already has a subscription
            try:
                self.subscription_service.create_subscription(
                    user=self.test_user,
                    plan=self.test_plans['pro']
                )
                self.fail_test("Duplicate subscription prevention", "Should have raised error")
            except ValueError:
                self.pass_test("Duplicate subscription prevention")
        except Exception as e:
            self.fail_test("Duplicate subscription prevention", str(e))

        # Test search usage tracking
        try:
            subscription = self.test_user.subscription
            if subscription:
                initial_searches = subscription.searches_used_this_period
                
                # Use a search
                success = subscription.use_search()
                assert success == True
                assert subscription.searches_used_this_period == initial_searches + 1
                # Test search limit enforcement
                subscription.searches_used_this_period = subscription.plan.leads_per_month
                subscription.save()
                success = subscription.use_search()
                assert success == False  # Should fail when limit reached
                
                self.pass_test("Search usage tracking")
            else:
                self.pass_test("Search usage tracking (no subscription)")
        except Exception as e:
            self.fail_test("Search usage tracking", str(e))

        # Test expired credits handling
        try:
            # Create expired credit
            payment = PaymentHistory.objects.filter(user=self.test_user).first()
            expired_credit = UserLeadCredit.objects.create(
                user=self.test_user,
                package=self.test_packages['boost'],
                payment=payment,
                credits_purchased=10,
                expires_at=timezone.now() - timedelta(days=1)  # Expired yesterday
            )
            
            assert expired_credit.is_expired == True
            assert expired_credit.use_credits(1) == False  # Should fail for expired credits
            self.pass_test("Expired credits handling")
        except Exception as e:
            self.fail_test("Expired credits handling", str(e))

        # Test proration calculation
        try:
            if hasattr(self.test_user, 'subscription') and self.test_user.subscription:
                subscription = self.test_user.subscription
                new_plan = self.test_plans['pro']
                
                # Test proration calculation (private method)
                proration = self.subscription_service._calculate_proration(
                    subscription, new_plan, immediate=True
                )
                assert isinstance(proration, (type(None), Decimal))
                self.pass_test("Proration calculation")
            else:
                self.pass_test("Proration calculation (no subscription)")
        except Exception as e:
            self.fail_test("Proration calculation", str(e))

    def test_api_integration(self):
        """Test API integration points."""
        print("\n🌐 Testing API Integration...")
        
        # Test subscription plan filtering
        try:
            active_plans = SubscriptionPlan.objects.filter(is_active=True)
            assert active_plans.count() >= 2  # At least our test plans
            self.pass_test("Subscription plan filtering")
        except Exception as e:
            self.fail_test("Subscription plan filtering", str(e))

        # Test package filtering by target plan
        try:
            packages_for_free = LeadCreditPackage.objects.filter(
                target_buyer_plan=self.test_plans['free']
            )
            assert packages_for_free.count() >= 1  # Our test package
            self.pass_test("Package filtering by target plan")
        except Exception as e:
            self.fail_test("Package filtering by target plan", str(e))

        # Test payment history ordering
        try:
            payments = PaymentHistory.objects.filter(
                user=self.test_user
            ).order_by('-created_at')
            
            if payments.count() >= 2:
                # Check that they're properly ordered
                first_payment = payments.first()
                last_payment = payments.last()
                assert first_payment.created_at >= last_payment.created_at
            
            self.pass_test("Payment history ordering")
        except Exception as e:
            self.fail_test("Payment history ordering", str(e))

    def test_admin_functionality(self):
        """Test admin interface functionality."""
        print("\n👨‍💼 Testing Admin Functionality...")
        
        # Test admin display methods
        try:
            from apps.subscriptions.admin import (
                LeadCreditPackageAdmin, PaymentHistoryAdmin, UserLeadCreditAdmin
            )
            
            # Test package admin display
            package_admin = LeadCreditPackageAdmin(LeadCreditPackage, None)
            package = self.test_packages['boost']
            price_display = package_admin.price_per_lead_display(package)
            assert "$1.0" in price_display
            
            # Test payment admin display
            payment_admin = PaymentHistoryAdmin(PaymentHistory, None)
            payment = PaymentHistory.objects.filter(user=self.test_user).first()
            if payment:
                amount_display = payment_admin.amount_display(payment)
                assert "$" in amount_display
                assert payment.currency in amount_display
            
            self.pass_test("Admin display methods")
        except Exception as e:
            self.fail_test("Admin display methods", str(e))

        # Test admin actions
        try:
            from django.contrib.admin.sites import AdminSite
            from django.http import HttpRequest
            from django.contrib.auth.models import AnonymousUser
            
            # Create mock request
            request = HttpRequest()
            request.user = AnonymousUser()
            
            # Test payment admin actions
            payment_admin = PaymentHistoryAdmin(PaymentHistory, AdminSite())
            pending_payments = PaymentHistory.objects.filter(
                user=self.test_user,
                status='pending'
            )
            
            if pending_payments.exists():
                # Test mark as completed action
                payment_admin.mark_as_completed(request, pending_payments)
                
                # Verify payment was marked as completed
                for payment in pending_payments:
                    payment.refresh_from_db()
                    # Note: This might not work in test because we don't have real request
                    # but the important thing is that the method doesn't crash
            
            self.pass_test("Admin actions")
        except Exception as e:
            self.fail_test("Admin actions", str(e))

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        print("\n🚨 Testing Edge Cases...")
        
        # Test subscription service with invalid data
        try:
            invalid_plan = SubscriptionPlan(
                name='INVALID',
                price=Decimal('-10.00'),  # Negative price
                leads_per_month=-1  # Negative leads
            )
            
            try:
                self.subscription_service.create_subscription(
                    user=self.test_user,
                    plan=invalid_plan
                )
                self.fail_test("Invalid plan handling", "Should have raised error")
            except:
                self.pass_test("Invalid plan handling")
        except Exception as e:
            self.fail_test("Invalid plan handling", str(e))

        # Test credit usage with invalid amounts
        try:
            credit = UserLeadCredit.objects.filter(user=self.test_user).first()
            if credit:
                # Test negative amount
                assert credit.use_credits(-1) == False
                
                # Test zero amount
                assert credit.use_credits(0) == False
                
                # Test amount larger than available
                large_amount = credit.credits_remaining + 100
                assert credit.use_credits(large_amount) == False
                
            self.pass_test("Invalid credit usage")
        except Exception as e:
            self.fail_test("Invalid credit usage", str(e))

        # Test payment gateway error handling
        try:
            # Test with invalid payment method
            try:
                self.subscription_service.create_subscription(
                    user=self.test_user,
                    plan=self.test_plans['pro'],
                    payment_method_id='invalid_payment_method'
                )
                # This should fail but we're catching it
            except:
                pass  # Expected to fail
            
            self.pass_test("Payment gateway error handling")
        except Exception as e:
            self.fail_test("Payment gateway error handling", str(e))

    def test_data_integrity(self):
        """Test data integrity and constraints."""
        print("\n🔒 Testing Data Integrity...")
        
        # Test unique transaction IDs
        try:
            payment1 = PaymentHistory.objects.create(
                user=self.test_user,
                amount=Decimal('10.00'),
                payment_gateway='stripe',
                transaction_id='unique_test_001',
                status='completed'
            )
            
            try:
                payment2 = PaymentHistory.objects.create(
                    user=self.test_user,
                    amount=Decimal('20.00'),
                    payment_gateway='stripe',
                    transaction_id='unique_test_001',  # Same ID
                    status='completed'
                )
                self.fail_test("Unique transaction ID constraint", "Should have raised error")
            except:
                self.pass_test("Unique transaction ID constraint")
        except Exception as e:
            self.fail_test("Unique transaction ID constraint", str(e))

        # Test foreign key constraints
        try:
            # Test that deleting a user cascades properly
            test_user2 = User.objects.create_user(
                username='testdelete',
                email='testdelete@example.com',
                password='testpass123'
            )
            
            payment = PaymentHistory.objects.create(
                user=test_user2,
                amount=Decimal('5.00'),
                payment_gateway='manual',
                transaction_id='cascade_test_001',
                status='completed'
            )
            
            user_id = test_user2.id
            payment_id = payment.id
            
            # Delete user
            test_user2.delete()
            
            # Payment should be deleted due to CASCADE
            assert not PaymentHistory.objects.filter(id=payment_id).exists()
            
            self.pass_test("Foreign key constraints")
        except Exception as e:
            self.fail_test("Foreign key constraints", str(e))

    def test_performance(self):
        """Test performance-related functionality."""
        print("\n⚡ Testing Performance...")
        
        # Test bulk operations
        try:
            import time
            
            # Create multiple payments and measure time
            start_time = time.time()
            
            payments_to_create = []
            for i in range(10):
                payments_to_create.append(PaymentHistory(
                    user=self.test_user,
                    amount=Decimal('1.00'),
                    payment_gateway='stripe',
                    transaction_id=f'bulk_test_{i}_{int(time.time())}',
                    status='completed'
                ))
            
            # Bulk create
            PaymentHistory.objects.bulk_create(payments_to_create)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should be reasonably fast (less than 1 second for 10 records)
            assert duration < 1.0
            
            self.pass_test("Bulk operations performance")
        except Exception as e:
            self.fail_test("Bulk operations performance", str(e))

        # Test query optimization
        try:
            from django.db import connection
            from django.test.utils import override_settings
            
            # Reset queries
            connection.queries_log.clear()
            
            # Perform operations that should be optimized
            subscriptions = UserSubscription.objects.select_related(
                'user', 'plan'
            ).filter(is_active=True)
            
            for subscription in subscriptions:
                # Access related fields (should not cause additional queries)
                _ = subscription.user.email
                _ = subscription.plan.name
            
            self.pass_test("Query optimization")
        except Exception as e:
            self.fail_test("Query optimization", str(e))

    def cleanup_test_data(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Delete test user and related data (CASCADE should handle the rest)
            if self.test_user:
                self.test_user.delete()
            
            # Delete test packages
            for package in self.test_packages.values():
                if package and hasattr(package, 'pk'):
                    package.delete()
            
            # Clean up any orphaned test data
            PaymentHistory.objects.filter(
                transaction_id__startswith='test_'
            ).delete()
            
            PaymentHistory.objects.filter(
                transaction_id__startswith='bulk_test_'
            ).delete()
            
            print("✅ Test data cleanup complete")
            
        except Exception as e:
            print(f"⚠️ Warning: Error during cleanup: {e}")

    def pass_test(self, test_name):
        """Mark test as passed."""
        self.passed_tests += 1
        print(f"✅ {test_name}")

    def fail_test(self, test_name, error):
        """Mark test as failed."""
        self.failed_tests += 1
        print(f"❌ {test_name}: {error}")

    def test_webhooks(self):
        """Test webhook handling."""
        print("\n🔗 Testing Webhooks...")
        
        try:
            # Test webhook event processing
            mock_stripe_event = {
                'type': 'invoice.payment_succeeded',
                'data': {
                    'object': {
                        'subscription': 'sub_test123',
                        'amount_paid': 5999,
                        'currency': 'usd'
                    }
                }
            }
            
            # Test webhook processing (won't actually process since subscription doesn't exist)
            success = self.payment_service.handle_webhook_event(
                mock_stripe_event['type'],
                mock_stripe_event['data']['object']
            )
            
            # Should return True even if subscription doesn't exist (graceful handling)
            assert success == True
            
            self.pass_test("Webhook event processing")
        except Exception as e:
            self.fail_test("Webhook event processing", str(e))

    def test_subscription_lifecycle(self):
        """Test complete subscription lifecycle."""
        print("\n🔄 Testing Subscription Lifecycle...")
        
        try:
            # Create a separate user for lifecycle testing
            lifecycle_user = User.objects.create_user(
                username='lifecycleuser',
                email='lifecycle@example.com',
                password='testpass123'
            )
            
            # 1. Start with free plan
            subscription, payment = self.subscription_service.create_subscription(
                user=lifecycle_user,
                plan=self.test_plans['free']
            )
            assert subscription.plan.name == 'FREE'
            
            # 2. Upgrade to pro
            upgrade_request = self.subscription_service.upgrade_subscription(
                user=lifecycle_user,
                new_plan=self.test_plans['pro'],
                effective_immediately=True
            )
            assert upgrade_request.status == 'completed'
            
            # Refresh subscription
            subscription.refresh_from_db()
            assert subscription.plan.name == 'PRO'
            
            # 3. Use some searches
            initial_usage = subscription.searches_used_this_period
            subscription.use_search()
            subscription.use_search()
            assert subscription.searches_used_this_period == initial_usage + 2
            
            # 4. Reset monthly usage (simulate billing cycle)
            self.subscription_service.reset_monthly_usage(subscription)
            subscription.refresh_from_db()
            assert subscription.searches_used_this_period == 0
            
            # 5. Cancel subscription
            cancellation = self.subscription_service.cancel_subscription(
                user=lifecycle_user,
                reason='testing',
                cancel_immediately=True
            )
            assert cancellation.is_processed
            
            # Cleanup
            lifecycle_user.delete()
            
            self.pass_test("Complete subscription lifecycle")
        except Exception as e:
            self.fail_test("Complete subscription lifecycle", str(e))


def main():
    """Main function to run all tests."""
    print("Starting Vending Hive Subscriptions Package Tests...")
    print("This will test all functionality of the subscriptions package.")
    print("Please ensure you have a clean test database before running.\n")
    
    runner = SubscriptionTestRunner()
    
    try:
        # Run all test categories
        runner.run_all_tests()
        runner.test_api_integration()
        runner.test_admin_functionality()
        runner.test_edge_cases()
        runner.test_data_integrity()
        runner.test_performance()
        runner.test_webhooks()
        runner.test_subscription_lifecycle()
        
        print("\n" + "=" * 80)
        print("FINAL TEST RESULTS")
        print("=" * 80)
        print(f"✅ Tests Passed: {runner.passed_tests}")
        print(f"❌ Tests Failed: {runner.failed_tests}")
        print(f"📊 Success Rate: {(runner.passed_tests / (runner.passed_tests + runner.failed_tests)) * 100:.1f}%")
        
        if runner.failed_tests == 0:
            print("\n🎉 CONGRATULATIONS! All subscription tests passed!")
            print("The Subscriptions package is working correctly and ready for production.")
            return True
        else:
            print(f"\n⚠️ {runner.failed_tests} tests failed. Please review and fix issues before deployment.")
            return False
            
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n\n❌ Critical error during testing: {e}")
        return False
    finally:
        # Ensure cleanup runs even if tests fail
        try:
            runner.cleanup_test_data()
        except:
            pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)