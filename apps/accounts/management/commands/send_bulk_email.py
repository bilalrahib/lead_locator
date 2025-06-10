from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.services import UserEmailService
from apps.accounts.models import UserActivity

User = get_user_model()


class Command(BaseCommand):
    help = 'Send bulk emails to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['welcome', 'verification', 'marketing'],
            required=True,
            help='Type of email to send'
        )
        parser.add_argument(
            '--filter',
            choices=['all', 'verified', 'unverified', 'premium', 'free'],
            default='all',
            help='Filter users to send to'
        )
        parser.add_argument(
            '--template',
            type=str,
            help='Template name for marketing emails'
        )
        parser.add_argument(
            '--subject',
            type=str,
            help='Subject for marketing emails'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show who would receive emails without sending'
        )

    def handle(self, *args, **options):
        email_type = options['type']
        user_filter = options['filter']
        dry_run = options['dry_run']

        # Build queryset based on filter
        queryset = User.objects.filter(is_active=True)

        if user_filter == 'verified':
            queryset = queryset.filter(email_verified=True)
        elif user_filter == 'unverified':
            queryset = queryset.filter(email_verified=False)
        elif user_filter == 'premium':
            queryset = queryset.filter(
                current_subscription__plan__name__in=['ELITE', 'PROFESSIONAL']
            )
        elif user_filter == 'free':
            queryset = queryset.filter(
                models.Q(current_subscription__isnull=True) |
                models.Q(current_subscription__plan__name='FREE')
            )

        users = queryset.distinct()
        
        self.stdout.write(f'Found {users.count()} users matching filter: {user_filter}')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No emails will be sent')
            )
            for user in users[:10]:  # Show first 10
                self.stdout.write(f'Would send to: {user.email}')
            if users.count() > 10:
                self.stdout.write(f'... and {users.count() - 10} more users')
            return

        # Send emails
        email_service = UserEmailService()
        sent_count = 0
        failed_count = 0

        for user in users:
            try:
                success = False
                
                if email_type == 'welcome':
                    success = email_service.send_welcome_email(user)
                elif email_type == 'verification':
                    if not user.email_verified:
                        user.generate_email_verification_token()
                        success = email_service.send_verification_email(user)
                elif email_type == 'marketing':
                    if options['template'] and options['subject']:
                        success = email_service.send_marketing_email(
                            user=user,
                            subject=options['subject'],
                            template_name=options['template']
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR('Marketing emails require --template and --subject')
                        )
                        return

                if success:
                    sent_count += 1
                    self.stdout.write(f'Sent to: {user.email}')
                else:
                    failed_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Failed to send to: {user.email}')
                    )

            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error sending to {user.email}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Bulk email completed! Sent: {sent_count}, Failed: {failed_count}'
            )
        )