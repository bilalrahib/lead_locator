from django.core.management.base import BaseCommand
from apps.project_core.services import NotificationService
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Send system notifications'

    def add_arguments(self, parser):
        parser.add_argument('title', type=str, help='Notification title')
        parser.add_argument('message', type=str, help='Notification message')
        parser.add_argument(
            '--type',
            type=str,
            choices=['info', 'warning', 'error', 'success', 'maintenance'],
            default='info',
            help='Notification type'
        )
        parser.add_argument(
            '--homepage',
            action='store_true',
            help='Show on homepage'
        )
        parser.add_argument(
            '--duration',
            type=int,
            help='Duration in hours (default: no end date)'
        )

    def handle(self, *args, **options):
        notification_service = NotificationService()
        
        end_date = None
        if options['duration']:
            end_date = timezone.now() + timedelta(hours=options['duration'])
        
        notification = notification_service.create_notification(
            title=options['title'],
            message=options['message'],
            notification_type=options['type'],
            show_on_homepage=options['homepage'],
            end_date=end_date
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Notification created: {notification.title} (ID: {notification.id})'
            )
        )