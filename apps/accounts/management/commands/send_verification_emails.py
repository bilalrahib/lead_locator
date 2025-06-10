from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.services import UserEmailService

User = get_user_model()


class Command(BaseCommand):
    help = 'Send verification emails to unverified users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Send to all unverified users'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Send to specific email address'
        )
        parser.add_argument(
            '--recent',
            type=int,
            help='Send to users registered in the last N days'
        )

    def handle(self, *args, **options):
        email_service = UserEmailService()
        
        if options['email']:
            # Send to specific user
            try:
                user = User.objects.get(email=options['email'])
                if user.email_verified:
                    self.stdout.write(
                        self.style.WARNING(f'User {user.email} is already verified')
                    )
                    return
                
                user.generate_email_verification_token()
                success = email_service.send_verification_email(user)
                
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f'Verification email sent to {user.email}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send email to {user.email}')
                    )
                    
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with email {options["email"]} not found')
                )
                
        elif options['recent']:
            # Send to recent users
            from django.utils import timezone
            from datetime import timedelta
            
            cutoff_date = timezone.now() - timedelta(days=options['recent'])
            users = User.objects.filter(
                email_verified=False,
                date_joined__gte=cutoff_date
            )
            
            self._send_bulk_verification_emails(users, email_service)
            
        elif options['all']:
            # Send to all unverified users
            users = User.objects.filter(email_verified=False)
            self._send_bulk_verification_emails(users, email_service)
            
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --all, --email, or --recent option')
            )

    def _send_bulk_verification_emails(self, users, email_service):
        """Send verification emails to multiple users."""
        total_users = users.count()
        sent_count = 0
        failed_count = 0
        
        self.stdout.write(f'Sending verification emails to {total_users} users...')
        
        for user in users:
            user.generate_email_verification_token()
            success = email_service.send_verification_email(user)
            
            if success:
                sent_count += 1
                self.stdout.write(f'✓ Sent to {user.email}')
            else:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to send to {user.email}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Completed! Sent: {sent_count}, Failed: {failed_count}'
            )
        )