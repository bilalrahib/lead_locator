import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, Mock
from .models import UserProfile, UserActivity
from .services import AuthService, UserService, UserEmailService
from .serializers import UserRegistrationSerializer, UserLoginSerializer

User = get_user_model()


class CustomUserModelTestCase(TestCase):
    """Test cases for CustomUser model."""

    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }

    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertFalse(user.email_verified)

    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(**self.user_data)
        
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(**self.user_data)
        expected = f"{user.email} (Test User)"
        self.assertEqual(str(user), expected)

    def test_full_name_property(self):
        """Test full_name property."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.full_name, 'Test User')
        
        # Test with missing names
        user.first_name = ''
        user.last_name = ''
        self.assertEqual(user.full_name, 'testuser')

    def test_account_locking(self):
        """Test account locking functionality."""
        user = User.objects.create_user(**self.user_data)
        
        # Test locking
        user.lock_account(duration_minutes=5)
        self.assertTrue(user.is_locked)
        self.assertTrue(user.is_account_locked)
        self.assertIsNotNone(user.lock_expires_at)
        
        # Test unlocking
        user.unlock_account()
        self.assertFalse(user.is_locked)
        self.assertFalse(user.is_account_locked)
        self.assertEqual(user.failed_login_attempts, 0)

    def test_failed_login_attempts(self):
        """Test failed login attempts handling."""
        user = User.objects.create_user(**self.user_data)
        
        # Test incrementing failed attempts
        for i in range(4):
            user.increment_failed_attempts()
            self.assertEqual(user.failed_login_attempts, i + 1)
            self.assertFalse(user.is_locked)
        
        # Fifth attempt should lock account
        user.increment_failed_attempts()
        self.assertEqual(user.failed_login_attempts, 5)
        self.assertTrue(user.is_locked)

    def test_email_verification_token(self):
        """Test email verification token generation and verification."""
        user = User.objects.create_user(**self.user_data)
        
        # Generate token
        token = user.generate_email_verification_token()
        self.assertIsNotNone(token)
        self.assertEqual(user.email_verification_token, token)
        self.assertIsNotNone(user.email_verification_sent_at)
        
        # Verify email
        self.assertTrue(user.verify_email(token))
        self.assertTrue(user.email_verified)
        self.assertEqual(user.email_verification_token, '')

    def test_password_reset_token(self):
        """Test password reset token generation and verification."""
        user = User.objects.create_user(**self.user_data)
        
        # Generate token
        token = user.generate_password_reset_token()
        self.assertIsNotNone(token)
        self.assertEqual(user.password_reset_token, token)
        self.assertIsNotNone(user.password_reset_expires_at)
        
        # Verify token
        self.assertTrue(user.verify_password_reset_token(token))
        
        # Clear token
        user.clear_password_reset_token()
        self.assertEqual(user.password_reset_token, '')
        self.assertIsNone(user.password_reset_expires_at)


class UserProfileModelTestCase(TestCase):
    """Test cases for UserProfile model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_profile_creation(self):
        """Test that profile is created automatically."""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, UserProfile)

    def test_completion_percentage(self):
        """Test profile completion percentage calculation."""
        profile = self.user.profile
        
        # Initially should be low
        initial_completion = profile.completion_percentage
        self.assertLess(initial_completion, 50)
        
        # Fill out profile
        profile.business_type = 'small_business'
        profile.years_in_business = 5
        profile.number_of_machines = 10
        profile.address_line1 = '123 Test St'
        profile.city = 'Test City'
        profile.state = 'TS'
        profile.zip_code = '12345'
        self.user.phone = '555-1234'
        self.user.company_name = 'Test Company'
        self.user.save()
        profile.save()
        
        # Should be higher now
        new_completion = profile.completion_percentage
        self.assertGreater(new_completion, initial_completion)

    def test_full_address(self):
        """Test full address property."""
        profile = self.user.profile
        profile.address_line1 = '123 Test St'
        profile.address_line2 = 'Apt 4'
        profile.city = 'Test City'
        profile.state = 'TS'
        profile.zip_code = '12345'
        profile.save()
        
        expected = '123 Test St, Apt 4, Test City, TS 12345'
        self.assertEqual(profile.full_address, expected)


class UserActivityModelTestCase(TestCase):
    """Test cases for UserActivity model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_log_activity(self):
        """Test logging user activity."""
        activity = UserActivity.log_activity(
            user=self.user,
            activity_type='login',
            description='Test login',
            metadata={'test': 'data'}
        )
        
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, 'login')
        self.assertEqual(activity.description, 'Test login')
        self.assertEqual(activity.metadata['test'], 'data')

    def test_activity_string_representation(self):
        """Test activity string representation."""
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='login',
            description='Test activity'
        )
        
        expected = f"{self.user.email} - Login"
        self.assertEqual(str(activity), expected)


class AuthServiceTestCase(TestCase):
    """Test cases for AuthService."""

    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }

    @patch('apps.accounts.services.auth_service.UserEmailService')
    def test_register_user(self, mock_email_service):
        """Test user registration."""
        mock_email_service.return_value.send_welcome_email.return_value = True
        mock_email_service.return_value.send_verification_email.return_value = True
        
        user = AuthService.register_user(self.user_data)
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertIsNotNone(user.email_verification_token)

    def test_login_user(self):
        """Test user login."""
        # Create user first
        user = User.objects.create_user(**self.user_data)
        
        # Test successful login
        logged_in_user, tokens = AuthService.login_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertEqual(logged_in_user, user)
        self.assertIsNotNone(tokens)
        self.assertIn('access', tokens)
        self.assertIn('refresh', tokens)

    def test_login_user_failure(self):
        """Test failed user login."""
        # Create user first
        User.objects.create_user(**self.user_data)
        
        # Test failed login
        logged_in_user, tokens = AuthService.login_user(
            email='test@example.com',
            password='wrongpassword'
        )
        
        self.assertIsNone(logged_in_user)
        self.assertIsNone(tokens)

    def test_change_password(self):
        """Test password change."""
        user = User.objects.create_user(**self.user_data)
        
        # Test successful password change
        success = AuthService.change_password(
            user=user,
            old_password='testpass123',
            new_password='newpass123'
        )
        
        self.assertTrue(success)
        user.refresh_from_db()
        self.assertTrue(user.check_password('newpass123'))

    @patch('apps.accounts.services.auth_service.UserEmailService')
    def test_request_password_reset(self, mock_email_service):
        """Test password reset request."""
        mock_email_service.return_value.send_password_reset_email.return_value = True
        
        user = User.objects.create_user(**self.user_data)
        
        success = AuthService.request_password_reset('test@example.com')
        
        self.assertTrue(success)
        user.refresh_from_db()
        self.assertIsNotNone(user.password_reset_token)


class UserServiceTestCase(TestCase):
    """Test cases for UserService."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_get_user_stats(self):
        """Test getting user statistics."""
        stats = UserService.get_user_stats(self.user)
        
        self.assertIn('account_info', stats)
        self.assertIn('activity_stats', stats)
        self.assertIn('profile_stats', stats)
        self.assertIn('subscription_stats', stats)

    def test_update_user_profile(self):
        """Test updating user profile."""
        profile_data = {
            'business_type': 'small_business',
            'years_in_business': 5,
            'number_of_machines': 10
        }
        
        profile = UserService.update_user_profile(self.user, profile_data)
        
        self.assertEqual(profile.business_type, 'small_business')
        self.assertEqual(profile.years_in_business, 5)
        self.assertEqual(profile.number_of_machines, 10)

    def test_search_users(self):
        """Test user search functionality."""
        # Create additional users
        User.objects.create_user(
            email='john@example.com',
            username='john',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        
        results = UserService.search_users('john')
        
        self.assertEqual(results['total_count'], 1)
        self.assertEqual(len(results['users']), 1)
        self.assertEqual(results['users'][0].first_name, 'John')


class UserRegistrationAPITestCase(APITestCase):
    """Test cases for user registration API."""

    def setUp(self):
        self.url = reverse('accounts:api_register')
        self.valid_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'terms_accepted': True
        }

    @patch('apps.accounts.services.auth_service.UserEmailService')
    def test_successful_registration(self, mock_email_service):
        """Test successful user registration."""
        mock_email_service.return_value.send_welcome_email.return_value = True
        mock_email_service.return_value.send_verification_email.return_value = True
        
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='test@example.com').exists())

    def test_registration_duplicate_email(self):
        """Test registration with duplicate email."""
        User.objects.create_user(
            email='test@example.com',
            username='existing',
            password='testpass123'
        )
        
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_password_mismatch(self):
        """Test registration with password mismatch."""
        data = self.valid_data.copy()
        data['password_confirm'] = 'differentpass'
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_registration_weak_password(self):
        """Test registration with weak password."""
        data = self.valid_data.copy()
        data['password'] = '123'
        data['password_confirm'] = '123'
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)


class UserLoginAPITestCase(APITestCase):
    """Test cases for user login API."""

    def setUp(self):
        self.url = reverse('accounts:api_login')
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_successful_login(self):
        """Test successful login."""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_locked_account(self):
        """Test login with locked account."""
        self.user.lock_account()
        
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Account is temporarily locked', str(response.data))

    def test_login_inactive_account(self):
        """Test login with inactive account."""
        self.user.is_active = False
        self.user.save()
        
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Account is disabled', str(response.data))


class UserProfileAPITestCase(APITestCase):
    """Test cases for user profile API."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('accounts:api_profile')

    def test_get_profile(self):
        """Test getting user profile."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_update_profile(self):
        """Test updating user profile."""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone': '555-1234'
        }
        
        response = self.client.patch(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.phone, '555-1234')

    def test_profile_unauthorized(self):
        """Test profile access without authentication."""
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordChangeAPITestCase(APITestCase):
    """Test cases for password change API."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('accounts:api_password_change')

    @patch('apps.accounts.services.email_service.UserEmailService')
    def test_successful_password_change(self, mock_email_service):
        """Test successful password change."""
        mock_email_service.return_value.send_password_changed_notification.return_value = True
        
        data = {
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))

    def test_password_change_wrong_current(self):
        """Test password change with wrong current password."""
        data = {
            'current_password': 'wrongpass',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', response.data)

    def test_password_change_confirmation_mismatch(self):
        """Test password change with confirmation mismatch."""
        data = {
            'current_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass'
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password_confirm', response.data)


class EmailVerificationAPITestCase(APITestCase):
    """Test cases for email verification API."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.url = reverse('accounts:api_email_verify')

    def test_successful_email_verification(self):
        """Test successful email verification."""
        token = self.user.generate_email_verification_token()
        
        data = {'token': token}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_email_verification_invalid_token(self):
        """Test email verification with invalid token."""
        data = {'token': 'invalid_token'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response.data)

    def test_email_verification_expired_token(self):
        """Test email verification with expired token."""
        token = self.user.generate_email_verification_token()
        
        # Make token expired
        self.user.email_verification_sent_at = timezone.now() - timedelta(days=8)
        self.user.save()
        
        data = {'token': token}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)