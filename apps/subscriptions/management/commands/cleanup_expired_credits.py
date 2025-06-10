from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.subscriptions.models import UserLeadCredit


class Command(BaseCommand):
    help = 'Clean up expired lead credits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually cleaning'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be deleted')
            )

        # Find expired credits
        expired_credits = UserLeadCredit.objects.filter(
            expires_at__lt=timezone.now()
        )

        count = expired_credits.count()
        self.stdout.write(f'Found {count} expired credit records')

        if dry_run:
            for credit in expired_credits:
                self.stdout.write(
                    f'Would delete: {credit.user.email} - {credit.package.name} (expired: {credit.expires_at})'
                )
        else:
            expired_credits.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {count} expired credit records')
            )