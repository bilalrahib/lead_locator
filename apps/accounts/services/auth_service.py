from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from typing import Dict, Optional, Tuple
import logging
from ..models import CustomUser, UserActivity

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for handling authentication operations.
    """

    @staticmethod
    def register_user(validated_data: Dict, request=None) -> CustomUser:
        """
        Register a new user.
        
        Args:
            validated_data: Validated registration data
            request: HTTP request object
            
        Returns:
            Created user instance
        """
        from .user_service import UserService
        from .email_service import UserEmailService
        
        
        user_data = validated_data.copy()
        user_data.pop('password_confirm', None)
        user_data.pop('terms_accepted', None)
        
        # Create user
        # user = CustomUser.objects.create_user(**validated_data)
        user = CustomUser.objects.create_user(**user_data)
        
        # Log activity
        if request:
            UserActivity.log_activity(
                user=user,
                activity_type='registration',
                description='User account created',
                request=request
            )
        
        # Send welcome email and verification email
        email_service = UserEmailService()
        email_service.send_welcome_email(user)
        email_service.send_verification_email(user)
        
        logger.info(f"New user registered: {user.email}")
        return user

    @staticmethod
    def login_user(email: str, password: str, request=None) -> Tuple[Optional[CustomUser], Optional[Dict]]:
        """
        Login user and return tokens.
        
        Args:
            email: User's email
            password: User's password
            request: HTTP request object
            
        Returns:
            Tuple of (user, tokens) or (None, None) if failed
        """
        from apps.project_core.utils.helpers import get_client_ip
        
        user = authenticate(email=email, password=password)
        
        if user:
            # Update last activity
            ip_address = get_client_ip(request) if request else None
            user.update_last_activity(ip_address)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            tokens = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
            
            # Log successful login
            if request:
                UserActivity.log_activity(
                    user=user,
                    activity_type='login',
                    description='Successful login',
                    request=request
                )
            
            logger.info(f"User logged in: {user.email}")
            return user, tokens
        
        return None, None

    @staticmethod
    def logout_user(user: CustomUser, request=None):
        """
        Logout user.
        
        Args:
            user: User instance
            request: HTTP request object
        """
        # Log logout activity
        if request:
            UserActivity.log_activity(
                user=user,
                activity_type='logout',
                description='User logged out',
                request=request
            )
        
        logger.info(f"User logged out: {user.email}")

    @staticmethod
    def change_password(user: CustomUser, old_password: str, new_password: str, request=None) -> bool:
        """
        Change user password.
        
        Args:
            user: User instance
            old_password: Current password
            new_password: New password
            request: HTTP request object
            
        Returns:
            True if successful, False otherwise
        """
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            
            # Log password change
            if request:
                UserActivity.log_activity(
                    user=user,
                    activity_type='password_change',
                    description='Password changed successfully',
                    request=request
                )
            
            logger.info(f"Password changed for user: {user.email}")
            return True
        
        return False

    @staticmethod
    def request_password_reset(email: str, request=None) -> bool:
        """
        Request password reset.
        
        Args:
            email: User's email
            request: HTTP request object
            
        Returns:
            True if email was sent (or user doesn't exist - for security)
        """
        from .email_service import UserEmailService
        
        try:
            user = CustomUser.objects.get(email__iexact=email)
            
            # Generate reset token
            token = user.generate_password_reset_token()
            
            # Send reset email
            email_service = UserEmailService()
            email_service.send_password_reset_email(user, token)
            
            logger.info(f"Password reset requested for: {user.email}")
            
        except CustomUser.DoesNotExist:
            # Don't reveal whether email exists or not
            logger.info(f"Password reset requested for non-existent email: {email}")
        
        return True

    @staticmethod
    def reset_password(token: str, new_password: str, request=None) -> bool:
        """
        Reset password with token.
        
        Args:
            token: Reset token
            new_password: New password
            request: HTTP request object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user = CustomUser.objects.get(password_reset_token=token)
            
            if user.verify_password_reset_token(token):
                user.set_password(new_password)
                user.clear_password_reset_token()
                user.save()
                
                # Log password reset
                if request:
                    UserActivity.log_activity(
                        user=user,
                        activity_type='password_change',
                        description='Password reset successfully',
                        request=request
                    )
                
                logger.info(f"Password reset completed for: {user.email}")
                return True
                
        except CustomUser.DoesNotExist:
            pass
        
        return False

    @staticmethod
    def verify_email(token: str, request=None) -> bool:
        """
        Verify email with token.
        
        Args:
            token: Verification token
            request: HTTP request object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user = CustomUser.objects.get(email_verification_token=token)
            
            if user.verify_email(token):
                # Log email verification
                if request:
                    UserActivity.log_activity(
                        user=user,
                        activity_type='email_verification',
                        description='Email verified successfully',
                        request=request
                    )
                
                logger.info(f"Email verified for: {user.email}")
                return True
                
        except CustomUser.DoesNotExist:
            pass
        
        return False

    @staticmethod
    def resend_verification_email(user: CustomUser, request=None) -> bool:
        """
        Resend email verification.
        
        Args:
            user: User instance
            request: HTTP request object
            
        Returns:
            True if sent successfully
        """
        from .email_service import UserEmailService
        
        if user.email_verified:
            return False  # Already verified
        
        # Generate new token
        token = user.generate_email_verification_token()
        
        # Send verification email
        email_service = UserEmailService()
        email_service.send_verification_email(user, token)
        
        logger.info(f"Verification email resent to: {user.email}")
        return True

    @staticmethod
    def check_account_security(user: CustomUser) -> Dict:
        """
        Check account security status.
        
        Args:
            user: User instance
            
        Returns:
            Dictionary with security status
        """
        security_score = 0
        recommendations = []
        
        # Check email verification
        if user.email_verified:
            security_score += 20
        else:
            recommendations.append("Verify your email address")
        
        # Check password strength (basic check)
        if user.last_login and (timezone.now() - user.last_login).days < 90:
            security_score += 20
        else:
            recommendations.append("Consider changing your password regularly")
        
        # Check profile completion
        try:
            profile_completion = user.profile.completion_percentage
            if profile_completion >= 80:
                security_score += 20
            else:
                recommendations.append("Complete your profile information")
        except:
            recommendations.append("Set up your profile")
        
        # Check recent activity
        if user.last_activity and (timezone.now() - user.last_activity).days < 7:
            security_score += 20
        
        # Check two-factor authentication (placeholder for future feature)
        security_score += 20  # Base score
        
        return {
            'security_score': security_score,
            'recommendations': recommendations,
            'email_verified': user.email_verified,
            'last_login': user.last_login,
            'last_activity': user.last_activity,
            'account_age_days': (timezone.now() - user.date_joined).days
        }