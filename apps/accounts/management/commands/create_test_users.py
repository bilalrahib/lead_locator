from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile
from faker import Faker
import random

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = 'Create test users for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of test users to create (default: 10)'
        )
        parser.add_argument(
            '--verified',
            action='store_true',
            help='Create users with verified emails'
        )

    def handle(self, *args, **options):
        count = options['count']
        verified = options['verified']
        
        self.stdout.write(f'Creating {count} test users...')
        
        business_types = ['individual', 'small_business', 'large_business', 'consultant']
        
        for i in range(count):
            # Create user
            email = fake.email()
            username = fake.user_name() + str(random.randint(100, 999))
            
            try:
                user = User.objects.create_user(
                    email=email,
                    username=username,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    phone=fake.phone_number()[:17],  # Limit to field length
                    company_name=fake.company(),
                    password='testpass123'
                )
                
                if verified:
                    user.email_verified = True
                    user.save()
                
                # Create profile
                profile = UserProfile.objects.get(user=user)
                profile.business_type = random.choice(business_types)
                profile.years_in_business = random.randint(0, 20)
                profile.number_of_machines = random.randint(1, 100)
                profile.address_line1 = fake.street_address()
                profile.city = fake.city()
                profile.state = fake.state()
                profile.zip_code = fake.zipcode()
                profile.target_locations = fake.text(max_nb_chars=200)
                profile.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {email}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating user {email}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {count} test users!')
        )