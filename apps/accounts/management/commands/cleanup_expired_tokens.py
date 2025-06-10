from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Clean up expired verification and reset tokens'

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
        
        # Clean expired email verification tokens (older than 7 days)
        email_verification_cutoff = timezone.now() - timedelta(days=7)
        expired_email_tokens = User.objects.filter(
            email_verification_sent_at__lt=email_verification_cutoff,
            email_verification_token__isnull=False
        ).exclude(email_verification_token='')
        
        email_count = expired_email_tokens.count()
        
        if dry_run:
            self.stdout.write(f'Would clean {email_count} expired email verification tokens')
        else:
            expired_email_tokens.update(
                email_verification_token='',
                email_verification_sent_at=None
            )
            self.stdout.write(f'Cleaned {email_count} expired email verification tokens')
        
        # Clean expired password reset tokens (older than 24 hours)
        password_reset_cutoff = timezone.now() - timedelta(hours=24)
        expired_reset_tokens = User.objects.filter(
            password_reset_expires_at__lt=timezone.now(),
            password_reset_token__isnull=False
        ).exclude(password_reset_token='')
        
        reset_count = expired_reset_tokens.count()
        
        if dry_run:
            self.stdout.write(f'Would clean {reset_count} expired password reset tokens')
        else:
            expired_reset_tokens.update(
                password_reset_token='',
                password_reset_expires_at=None
            )
            self.stdout.write(f'Cleaned {reset_count} expired password reset tokens')
        
        # Unlock accounts with expired locks
        expired_locks = User.objects.filter(
            is_locked=True,
            lock_expires_at__lt=timezone.now()
        )
        
        unlock_count = expired_locks.count()
        
        if dry_run:
            self.stdout.write(f'Would unlock {unlock_count} accounts with expired locks')
        else:
            for user in expired_locks:
                user.unlock_account()
            self.stdout.write(f'Unlocked {unlock_count} accounts with expired locks')
        
        total_cleaned = email_count + reset_count + unlock_count
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Would clean a total of {total_cleaned} items')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Cleanup completed! Total items cleaned: {total_cleaned}')
            )