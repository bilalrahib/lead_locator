from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.project_core.models import ContactMessage, SystemNotification, SupportTicket


class Command(BaseCommand):
    help = 'Clean up old data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete data older than specified days (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.SUCCESS(f'Cleaning up data older than {days} days...')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be deleted')
            )

        # Clean up old contact messages
        old_messages = ContactMessage.objects.filter(
            created_at__lt=cutoff_date,
            is_read=True
        )
        message_count = old_messages.count()
        
        if dry_run:
            self.stdout.write(f'Would delete {message_count} old contact messages')
        else:
            old_messages.delete()
            self.stdout.write(f'Deleted {message_count} old contact messages')

        # Clean up old inactive notifications
        old_notifications = SystemNotification.objects.filter(
            created_at__lt=cutoff_date,
            is_active=False
        )
        notification_count = old_notifications.count()
        
        if dry_run:
            self.stdout.write(f'Would delete {notification_count} old notifications')
        else:
            old_notifications.delete()
            self.stdout.write(f'Deleted {notification_count} old notifications')

        # Clean up resolved support tickets older than specified days
        old_tickets = SupportTicket.objects.filter(
            resolved_at__lt=cutoff_date,
            status__in=['resolved', 'closed']
        )
        ticket_count = old_tickets.count()
        
        if dry_run:
            self.stdout.write(f'Would delete {ticket_count} old support tickets')
        else:
            old_tickets.delete()
            self.stdout.write(f'Deleted {ticket_count} old support tickets')

        self.stdout.write(
            self.style.SUCCESS('Data cleanup completed!')
        )