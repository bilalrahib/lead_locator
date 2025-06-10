from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.project_core.models import SubscriptionPlan, SystemNotification
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up initial data for Vending Hive'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create a superuser',
        )
        parser.add_argument(
            '--superuser-email',
            type=str,
            help='Superuser email',
            default='admin@vendinghive.com'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Setting up initial data for Vending Hive...')
        )

        # Create subscription plans
        self.create_subscription_plans()
        
        # Create initial notifications
        self.create_initial_notifications()
        
        # Create superuser if requested
        if options['create_superuser']:
            self.create_superuser(options['superuser_email'])

        self.stdout.write(
            self.style.SUCCESS('Initial data setup completed!')
        )

    def create_subscription_plans(self):
        """Create initial subscription plans."""
        plans_data = [
            {
                'name': 'FREE',
                'price': 0.00,
                'leads_per_month': 3,
                'leads_per_search_range': '10',
                'script_templates_count': 1,
                'regeneration_allowed': False,
                'description': 'Perfect for getting started with vending machine placement.'
            },
            {
                'name': 'STARTER',
                'price': 29.99,
                'leads_per_month': 10,
                'leads_per_search_range': '10-15',
                'script_templates_count': 5,
                'regeneration_allowed': True,
                'description': 'Great for small vending operations with basic needs.'
            },
            {
                'name': 'PRO',
                'price': 59.99,
                'leads_per_month': 25,
                'leads_per_search_range': '15-20',
                'script_templates_count': 10,
                'regeneration_allowed': True,
                'description': 'Perfect for growing businesses with multiple locations.'
            },
            {
                'name': 'ELITE',
                'price': 99.99,
                'leads_per_month': 50,
                'leads_per_search_range': '20-25',
                'script_templates_count': 20,
                'regeneration_allowed': True,
                'description': 'Advanced features for serious vending entrepreneurs.'
            },
            {
                'name': 'PROFESSIONAL',
                'price': 199.99,
                'leads_per_month': 100,
                'leads_per_search_range': '25-30',
                'script_templates_count': 999,  # Unlimited
                'regeneration_allowed': True,
                'description': 'Full-featured plan for vending consultants and large operations.'
            }
        ]

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created subscription plan: {plan.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Subscription plan already exists: {plan.name}')
                )

    def create_initial_notifications(self):
        """Create initial system notifications."""
        notifications_data = [
            {
                'title': 'Welcome to Vending Hive!',
                'message': 'Thank you for joining Vending Hive. Explore our features and start finding great locations for your vending machines.',
                'notification_type': 'info',
                'show_on_homepage': True,
                'is_active': True
            }
        ]

        for notification_data in notifications_data:
            notification, created = SystemNotification.objects.get_or_create(
                title=notification_data['title'],
                defaults=notification_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created notification: {notification.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Notification already exists: {notification.title}')
                )

    def create_superuser(self, email):
        """Create a superuser if it doesn't exist."""
        try:
            if not User.objects.filter(email=email).exists():
                User.objects.create_superuser(
                    username='admin',
                    email=email,
                    password='admin123!',
                    first_name='Admin',
                    last_name='User'
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Superuser created with email: {email}')
                )
                self.stdout.write(
                    self.style.WARNING('Default password: admin123! (Please change this!)')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User with email {email} already exists')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            )