from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.project_core.models import UserSubscription
from apps.subscriptions.services import SubscriptionService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process subscription renewals and reset monthly usage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Find subscriptions that need renewal (ended yesterday or today)
        cutoff_date = timezone.now() + timedelta(days=1)
        subscriptions_to_renew = UserSubscription.objects.filter(
            is_active=True,
            end_date__lte=cutoff_date
        )

        count = subscriptions_to_renew.count()
        self.stdout.write(f'Found {count} subscriptions to process')

        if dry_run:
            for subscription in subscriptions_to_renew:
                self.stdout.write(
                    f'Would renew: {subscription.user.email} - {subscription.plan.name}'
                )
            return

        subscription_service = SubscriptionService()
        processed = 0
        failed = 0

        for subscription in subscriptions_to_renew:
            try:
                subscription_service.reset_monthly_usage(subscription)
                processed += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Renewed: {subscription.user.email} - {subscription.plan.name}'
                    )
                )
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to renew {subscription.user.email}: {e}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {processed} subscriptions, {failed} failed'
            )
        )