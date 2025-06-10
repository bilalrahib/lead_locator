from django.shortcuts import render, get_object_or_404
from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, UserProfile, UserActivity
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserProfileUpdateSerializer, PasswordChangeSerializer, PasswordResetSerializer,
    PasswordResetConfirmSerializer, EmailVerificationSerializer, EmailChangeSerializer,
    UserDeleteSerializer, UserProfileDetailSerializer, UserProfileCreateSerializer,
    UserActivitySerializer, UserStatsSerializer
)
from .services import AuthService, UserService, UserEmailService
import logging

logger = logging.getLogger(__name__)


# Authentication Views
class UserRegistrationAPIView(generics.CreateAPIView):
    """API endpoint for user registration."""
    
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        # user = AuthService.register_user(
        #     validated_data=serializer.validated_data,
        #     request=self.request
        # )
        user = serializer.save()  # Use serializer.save() instead of AuthService
        
        # Log successful registration
        UserActivity.log_activity(
            user=user,
            activity_type='registration',
            description='User registered successfully',
            request=self.request
        )


class UserLoginAPIView(APIView):
    """API endpoint for user login."""
    
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            remember_me = serializer.validated_data.get('remember_me', False)
            
            user, tokens = AuthService.login_user(
                email=email,
                password=password,
                request=request
            )
            
            if user and tokens:
                # Adjust token expiry if remember_me is True
                if remember_me:
                    # Extend refresh token expiry to 30 days
                    refresh = RefreshToken(tokens['refresh'])
                    refresh.set_exp(lifetime=30 * 24 * 60 * 60)  # 30 days
                    tokens['refresh'] = str(refresh)
                
                return Response({
                    'user': UserProfileSerializer(user).data,
                    'tokens': tokens,
                    'message': 'Login successful'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutAPIView(APIView):
    """API endpoint for user logout."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            AuthService.logout_user(request.user, request)
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return Response({
                'message': 'Logout completed'
            }, status=status.HTTP_200_OK)


# Profile Views
class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """API endpoint for user profile management."""
    
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    def perform_update(self, serializer):
        serializer.save()
        
        # Log profile update
        UserActivity.log_activity(
            user=self.request.user,
            activity_type='profile_update',
            description='Profile updated',
            request=self.request
        )


class UserProfileDetailAPIView(generics.RetrieveUpdateAPIView):

    """API endpoint for detailed user profile management."""
    
    serializer_class = UserProfileDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileCreateSerializer
        return UserProfileDetailSerializer


    def perform_create(self, serializer):
        profile = UserService.update_user_profile(
            user=self.request.user,
            profile_data=serializer.validated_data
        )
        return profile

    def perform_update(self, serializer):
        profile = UserService.update_user_profile(
            user=self.request.user,
            profile_data=serializer.validated_data
        )
        return profile


# Password Management Views
class PasswordChangeAPIView(APIView):
    """API endpoint for changing password."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log password change
            UserActivity.log_activity(
                user=user,
                activity_type='password_change',
                description='Password changed successfully',
                request=request
            )
            
            # Send notification email
            email_service = UserEmailService()
            email_service.send_password_changed_notification(user)
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestAPIView(APIView):
    """API endpoint for requesting password reset."""
    
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            AuthService.request_password_reset(email, request)
            
            return Response({
                'message': 'If an account with this email exists, you will receive a password reset link.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmAPIView(APIView):
    """API endpoint for confirming password reset."""
    
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log password reset
            UserActivity.log_activity(
                user=user,
                activity_type='password_change',
                description='Password reset completed',
                request=request
            )
            
            # Send notification email
            email_service = UserEmailService()
            email_service.send_password_changed_notification(user)
            
            return Response({
                'message': 'Password reset successful'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Email Management Views
class EmailVerificationAPIView(APIView):
    """API endpoint for email verification."""
    
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        
        if serializer.is_valid():
            return Response({
                'message': 'Email verified successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationResendAPIView(APIView):
    """API endpoint for resending email verification."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        if user.email_verified:
            return Response({
                'message': 'Email is already verified'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        success = AuthService.resend_verification_email(user, request)
        
        if success:
            return Response({
                'message': 'Verification email sent'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to send verification email'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailChangeAPIView(APIView):
    """API endpoint for changing email address."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EmailChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            old_email = request.user.email
            user = serializer.save()
            
            # Log email change
            UserActivity.log_activity(
                user=user,
                activity_type='email_change',
                description=f'Email changed from {old_email} to {user.email}',
                request=request,
                metadata={'old_email': old_email, 'new_email': user.email}
            )
            
            # Send notification emails
            email_service = UserEmailService()
            email_service.send_email_changed_notification(user, old_email)
            email_service.send_verification_email(user)
            
            return Response({
                'message': 'Email changed successfully. Please verify your new email address.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# User Data and Statistics Views
class UserStatsAPIView(APIView):
    """API endpoint for user statistics."""
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = UserService.get_user_stats(request.user)
        return Response(stats, status=status.HTTP_200_OK)


class UserDashboardAPIView(APIView):
    """API endpoint for user dashboard data."""
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dashboard_data = UserService.get_user_dashboard_data(request.user)
        return Response(dashboard_data, status=status.HTTP_200_OK)


class UserActivityListAPIView(generics.ListAPIView):
    """API endpoint for user activity list."""
    
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        activity_type = self.request.query_params.get('type')
        queryset = UserActivity.objects.filter(user=self.request.user)
        
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        return queryset.order_by('-created_at')


# Account Management Views
class UserDeleteAPIView(APIView):
    """API endpoint for account deletion."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserDeleteSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Log account deletion
            UserActivity.log_activity(
                user=user,
                activity_type='account_deleted',
                description='Account deletion requested',
                request=request
            )
            
            return Response({
                'message': 'Account deletion processed'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Security Views
class AccountSecurityAPIView(APIView):
    """API endpoint for account security information."""
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        security_info = AuthService.check_account_security(request.user)
        return Response(security_info, status=status.HTTP_200_OK)


# Admin Views (for staff users)
class UserSearchAPIView(APIView):
    """API endpoint for searching users (admin only)."""
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        query = request.query_params.get('q', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        if not query:
            return Response({
                'error': 'Search query is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = UserService.search_users(query, page, page_size)
        
        # Serialize users
        users_data = []
        for user in results['users']:
            users_data.append({
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'date_joined': user.date_joined,
                'last_login': user.last_login,
                'is_active': user.is_active,
                'subscription_status': user.subscription_status,
            })
        
        return Response({
            'users': users_data,
            'pagination': {
                'total_count': results['total_count'],
                'page': results['page'],
                'total_pages': results['total_pages'],
                'has_next': results['has_next'],
                'has_previous': results['has_previous'],
            }
        }, status=status.HTTP_200_OK)


# Health Check Views
@api_view(['GET'])
@permission_classes([AllowAny])
def accounts_health_check(request):
    """Health check for accounts app."""
    try:
        # Test database connection
        user_count = CustomUser.objects.count()
        
        return Response({
            'status': 'healthy',
            'total_users': user_count,
            'app': 'accounts'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Accounts health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'app': 'accounts'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)