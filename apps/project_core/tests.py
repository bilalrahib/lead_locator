import json
import uuid
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, Mock
from .models import (
    SupportTicket, WeatherLocation, SystemNotification, 
    ContactMessage, SubscriptionPlan
)
from .services import WeatherService, EmailService, NotificationService
from .utils.helpers import get_client_ip, format_phone_number, generate_unique_code
from .utils.validators import validate_zip_code, validate_phone_number

User = get_user_model()


class ProjectCoreModelsTestCase(TestCase):
    """Test cases for Project Core models."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_support_ticket_creation(self):
        """Test support ticket creation."""
        ticket = SupportTicket.objects.create(
            user=self.user,
            subject='Test Issue',
            description='This is a test support ticket.',
            priority='medium'
        )
        
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.subject, 'Test Issue')
        self.assertEqual(ticket.status, 'open')
        self.assertTrue(ticket.is_open)
        self.assertIsNone(ticket.resolved_at)

    def test_support_ticket_resolution(self):
        """Test support ticket resolution."""
        ticket = SupportTicket.objects.create(
            user=self.user,
            subject='Test Issue',
            description='This is a test support ticket.'
        )
        
        # Resolve the ticket
        ticket.status = 'resolved'
        ticket.save()
        
        self.assertEqual(ticket.status, 'resolved')
        self.assertFalse(ticket.is_open)
        self.assertIsNotNone(ticket.resolved_at)

    def test_weather_location_creation(self):
        """Test weather location creation."""
        location = WeatherLocation.objects.create(
            user=self.user,
            address='123 Main St, New York, NY',
            zip_code='10001',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            city='New York',
            state='NY',
            country='US'
        )
        
        self.assertEqual(location.user, self.user)
        self.assertEqual(location.zip_code, '10001')
        self.assertEqual(location.coordinates, '40.7128,-74.0060')

    def test_system_notification_current_property(self):
        """Test system notification current property."""
        # Active notification
        active_notification = SystemNotification.objects.create(
            title='Active Notification',
            message='This is active.',
            is_active=True,
            start_date=timezone.now() - timedelta(hours=1)
        )
        self.assertTrue(active_notification.is_current)
        
        # Inactive notification
        inactive_notification = SystemNotification.objects.create(
            title='Inactive Notification',
            message='This is inactive.',
            is_active=False
        )
        self.assertFalse(inactive_notification.is_current)
        
        # Future notification
        future_notification = SystemNotification.objects.create(
            title='Future Notification',
            message='This is in the future.',
            is_active=True,
            start_date=timezone.now() + timedelta(hours=1)
        )
        self.assertFalse(future_notification.is_current)
        
        # Expired notification
        expired_notification = SystemNotification.objects.create(
            title='Expired Notification',
            message='This is expired.',
            is_active=True,
            start_date=timezone.now() - timedelta(hours=2),
            end_date=timezone.now() - timedelta(hours=1)
        )
        self.assertFalse(expired_notification.is_current)

    def test_contact_message_creation(self):
        """Test contact message creation."""
        message = ContactMessage.objects.create(
            name='John Doe',
            email='john@example.com',
            phone='555-1234',
            subject='Test Subject',
            message='This is a test message.',
            ip_address='192.168.1.1'
        )
        
        self.assertEqual(message.name, 'John Doe')
        self.assertEqual(message.email, 'john@example.com')
        self.assertFalse(message.is_read)

    def test_subscription_plan_properties(self):
        """Test subscription plan properties."""
        free_plan = SubscriptionPlan.objects.create(
            name='FREE',
            price=Decimal('0.00'),
            leads_per_month=3,
            leads_per_search_range='10',
            script_templates_count=1,
            description='Free plan'
        )
        
        premium_plan = SubscriptionPlan.objects.create(
            name='ELITE',
            price=Decimal('99.99'),
            leads_per_month=50,
            leads_per_search_range='20-25',
            script_templates_count=20,
            description='Elite plan'
        )
        
        self.assertTrue(free_plan.is_free)
        self.assertFalse(free_plan.is_premium)
        self.assertFalse(premium_plan.is_free)
        self.assertTrue(premium_plan.is_premium)


class ProjectCoreAPITestCase(APITestCase):
    """Test cases for Project Core API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_homepage_data_api(self):
        """Test homepage data API endpoint."""
        # Create subscription plans
        SubscriptionPlan.objects.create(
            name='FREE',
            price=Decimal('0.00'),
            leads_per_month=3,
            leads_per_search_range='10',
            script_templates_count=1,
            description='Free plan'
        )
        
        url = reverse('project_core:homepage_data')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('company_name', response.data)
        self.assertIn('subscription_plans', response.data)
        self.assertIn('features', response.data)

    def test_contact_message_creation_api(self):
        """Test contact message creation API."""
        url = reverse('project_core:contact_create')
        data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '555-1234',
            'subject': 'Test Subject',
            'message': 'This is a test message from the API.'
        }
        
        # Allow unauthenticated access for contact form
        self.client.force_authenticate(user=None)
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ContactMessage.objects.filter(email='john@example.com').exists())

    def test_support_ticket_creation_api(self):
        """Test support ticket creation API."""
        url = reverse('project_core:support_tickets')
        data = {
            'subject': 'API Test Ticket',
            'description': 'This is a test ticket created via API.',
            'priority': 'high'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SupportTicket.objects.filter(
            user=self.user,
            subject='API Test Ticket'
        ).exists())

    def test_support_ticket_list_api(self):
        """Test support ticket list API."""
        # Create test tickets
        SupportTicket.objects.create(
            user=self.user,
            subject='Ticket 1',
            description='Description 1'
        )
        SupportTicket.objects.create(
            user=self.user,
            subject='Ticket 2',
            description='Description 2'
        )
        
        url = reverse('project_core:support_tickets')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_weather_location_api(self):
        """Test weather location API."""
        url = reverse('project_core:weather_location')
        data = {
            'address': '123 Main St, New York, NY',
            'zip_code': '10001'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(WeatherLocation.objects.filter(user=self.user).exists())

    @patch('apps.project_core.services.weather_service.requests.get')
    def test_weather_data_api(self, mock_get):
        """Test weather data API."""
        # Create weather location
        WeatherLocation.objects.create(
            user=self.user,
            address='123 Main St',
            zip_code='10001'
        )
        
        # Mock weather API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'name': 'New York',
            'main': {
                'temp': 72.5,
                'feels_like': 75.0,
                'humidity': 65,
                'pressure': 1013
            },
            'weather': [{
                'description': 'clear sky',
                'icon': '01d'
            }],
            'wind': {
                'speed': 5.5
            },
            'visibility': 10000
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        url = reverse('project_core:weather_data')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('temperature', response.data)
        self.assertIn('description', response.data)

    def test_notifications_api(self):
        """Test notifications API."""
        # Create test notifications
        SystemNotification.objects.create(
            title='Test Notification',
            message='This is a test notification.',
            is_active=True
        )
        
        url = reverse('project_core:notifications')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_health_check_api(self):
        """Test health check API."""
        url = reverse('project_core:health_check')
        # Allow unauthenticated access
        self.client.force_authenticate(user=None)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')


class WeatherServiceTestCase(TestCase):
    """Test cases for Weather Service."""

    def setUp(self):
        """Set up test data."""
        self.weather_service = WeatherService()

    @patch('apps.project_core.services.weather_service.requests.get')
    def test_get_weather_by_zip_success(self, mock_get):
        """Test successful weather fetch by ZIP code."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'name': 'New York',
            'main': {
                'temp': 72.5,
                'feels_like': 75.0,
                'humidity': 65,
                'pressure': 1013
            },
            'weather': [{
                'description': 'clear sky',
                'icon': '01d'
            }],
            'wind': {
                'speed': 5.5
            },
            'visibility': 10000
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.weather_service.get_weather_by_zip('10001')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['location'], 'New York')
        self.assertEqual(result['temperature'], 73)  # Rounded
        self.assertEqual(result['humidity'], 65)

    @patch('apps.project_core.services.weather_service.requests.get')
    def test_get_weather_by_zip_error(self, mock_get):
        """Test weather fetch error handling."""
        mock_get.side_effect = Exception('API Error')
        
        result = self.weather_service.get_weather_by_zip('10001')
        
        self.assertIsNone(result)

    def test_no_api_key(self):
        """Test behavior when API key is not configured."""
        service = WeatherService()
        service.api_key = ''
        
        result = service.get_weather_by_zip('10001')
        
        self.assertIsNone(result)


class EmailServiceTestCase(TestCase):
    """Test cases for Email Service."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.email_service = EmailService()

    def test_send_support_ticket_confirmation(self):
        """Test support ticket confirmation email."""
        ticket = SupportTicket.objects.create(
            user=self.user,
            subject='Test Ticket',
            description='Test description'
        )
        
        result = self.email_service.send_support_ticket_confirmation(ticket)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(ticket.user.email, mail.outbox[0].to)

    def test_send_contact_form_notification(self):
        """Test contact form notification email."""
        contact_message = ContactMessage.objects.create(
            name='John Doe',
            email='john@example.com',
            subject='Test Subject',
            message='Test message'
        )
        
        result = self.email_service.send_contact_form_notification(contact_message)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_welcome_email(self):
        """Test welcome email."""
        result = self.email_service.send_welcome_email(self.user)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)


class NotificationServiceTestCase(TestCase):
    """Test cases for Notification Service."""

    def setUp(self):
        """Set up test data."""
        self.notification_service = NotificationService()

    def test_get_active_notifications(self):
        """Test getting active notifications."""
        # Create active notification
        active_notification = SystemNotification.objects.create(
            title='Active',
            message='Active notification',
            is_active=True
        )
        
        # Create inactive notification
        SystemNotification.objects.create(
            title='Inactive',
            message='Inactive notification',
            is_active=False
        )
        
        notifications = self.notification_service.get_active_notifications()
        
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].id, active_notification.id)

    def test_create_notification(self):
        """Test creating notification."""
        notification = self.notification_service.create_notification(
            title='Test Notification',
            message='Test message',
            notification_type='info'
        )
        
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, 'Test Notification')
        self.assertTrue(notification.is_active)

    def test_deactivate_notification(self):
        """Test deactivating notification."""
        notification = SystemNotification.objects.create(
            title='Test',
            message='Test message',
            is_active=True
        )
        
        result = self.notification_service.deactivate_notification(notification.id)
        
        self.assertTrue(result)
        notification.refresh_from_db()
        self.assertFalse(notification.is_active)

    def test_create_maintenance_notification(self):
        """Test creating maintenance notification."""
        start_time = timezone.now() + timedelta(hours=1)
        end_time = timezone.now() + timedelta(hours=3)
        
        notification = self.notification_service.create_maintenance_notification(
            start_time=start_time,
            end_time=end_time
        )
        
        self.assertEqual(notification.notification_type, 'maintenance')
        self.assertEqual(notification.start_date, start_time)
        self.assertEqual(notification.end_date, end_time)


class UtilsTestCase(TestCase):
    """Test cases for utility functions."""

    def test_get_client_ip(self):
        """Test getting client IP from request."""
        from django.test import RequestFactory
        
        factory = RequestFactory()
        
        # Test with X-Forwarded-For header
        request = factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.1, 10.0.0.1'
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
        
        # Test with REMOTE_ADDR
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.2'
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.2')

    def test_format_phone_number(self):
        """Test phone number formatting."""
        # Test 10-digit number
        formatted = format_phone_number('5551234567')
        self.assertEqual(formatted, '(555) 123-4567')
        
        # Test 11-digit number with country code
        formatted = format_phone_number('15551234567')
        self.assertEqual(formatted, '+1 (555) 123-4567')
        
        # Test already formatted number
        formatted = format_phone_number('(555) 123-4567')
        self.assertEqual(formatted, '(555) 123-4567')

    def test_generate_unique_code(self):
        """Test unique code generation."""
        code = generate_unique_code(8)
        self.assertEqual(len(code), 8)
        
        # Test that codes are different
        code1 = generate_unique_code(10)
        code2 = generate_unique_code(10)
        self.assertNotEqual(code1, code2)

    def test_validate_zip_code(self):
        """Test ZIP code validation."""
        # Valid ZIP codes
        self.assertEqual(validate_zip_code('12345'), '12345')
        self.assertEqual(validate_zip_code('12345-6789'), '123456789')
        self.assertEqual(validate_zip_code('12345 6789'), '123456789')
        
        # Invalid ZIP codes
        with self.assertRaises(Exception):
            validate_zip_code('1234')
        
        with self.assertRaises(Exception):
            validate_zip_code('abcde')

    def test_validate_phone_number(self):
        """Test phone number validation."""
        # Valid phone numbers
        self.assertEqual(validate_phone_number('5551234567'), '5551234567')
        self.assertEqual(validate_phone_number('(555) 123-4567'), '5551234567')
        self.assertEqual(validate_phone_number('15551234567'), '5551234567')
        
        # Invalid phone numbers
        with self.assertRaises(Exception):
            validate_phone_number('123')
        
        with self.assertRaises(Exception):
            validate_phone_number('abc123def4567')


class WebViewsTestCase(TestCase):
    """Test cases for web views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_homepage_view(self):
        """Test homepage view."""
        # Create subscription plans
        SubscriptionPlan.objects.create(
            name='FREE',
            price=Decimal('0.00'),
            leads_per_month=3,
            leads_per_search_range='10',
            script_templates_count=1,
            description='Free plan'
        )
        
        url = reverse('project_core:homepage')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vending Hive')
        self.assertContains(response, 'AI-Powered')

    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        
        url = reverse('project_core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_dashboard_view_anonymous(self):
        """Test dashboard view redirects anonymous users."""
        url = reverse('project_core:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect to login


class ManagementCommandsTestCase(TestCase):
    """Test cases for management commands."""

    def test_setup_initial_data_command(self):
        """Test setup_initial_data management command."""
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('setup_initial_data', stdout=out)
        
        # Check that subscription plans were created
        self.assertTrue(SubscriptionPlan.objects.exists())
        self.assertEqual(SubscriptionPlan.objects.count(), 5)
        
        # Check that notifications were created
        self.assertTrue(SystemNotification.objects.exists())

    def test_cleanup_old_data_command(self):
        """Test cleanup_old_data management command."""
        from django.core.management import call_command
        from io import StringIO
        
        # Create old data
        old_date = timezone.now() - timedelta(days=100)
        ContactMessage.objects.create(
            name='Old Contact',
            email='old@example.com',
            subject='Old Subject',
            message='Old message',
            is_read=True,
            created_at=old_date
        )
        
        out = StringIO()
        call_command('cleanup_old_data', '--days=90', '--dry-run', stdout=out)
        
        # In dry-run mode, data should still exist
        self.assertTrue(ContactMessage.objects.exists())
        
        # Run actual cleanup
        call_command('cleanup_old_data', '--days=90', stdout=out)
        
        # Data should be cleaned up
        self.assertFalse(ContactMessage.objects.exists())