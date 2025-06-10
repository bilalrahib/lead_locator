from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.shortcuts import redirect
from django.http import JsonResponse
from apps.project_core.utils.helpers import get_client_ip
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class UserActivityMiddleware:
    """
    Middleware to track user activity and update last_activity timestamp.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Update user activity before processing request
        if request.user.is_authenticated:
            # Update last activity timestamp
            ip_address = get_client_ip(request)
            request.user.update_last_activity(ip_address)

        response = self.get_response(request)
        return response


class AccountLockMiddleware:
    """
    Middleware to check for locked accounts and redirect appropriately.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # URLs that should be accessible even when account is locked
        self.allowed_urls = [
            '/accounts/api/v1/accounts/logout/',
            '/accounts/api/v1/accounts/profile/',
            '/admin/logout/',
        ]

    def __call__(self, request):
        if (request.user.is_authenticated and 
            request.user.is_account_locked and 
            not request.path.startswith('/admin/') and
            request.path not in self.allowed_urls):
            
            # Check if this is an API request
            if (request.path.startswith('/api/') or 
                request.META.get('HTTP_ACCEPT', '').startswith('application/json')):
                
                return JsonResponse({
                    'error': 'Account is temporarily locked',
                    'locked_until': request.user.lock_expires_at.isoformat() if request.user.lock_expires_at else None,
                    'reason': 'Too many failed login attempts'
                }, status=423)  # 423 Locked
            
            # For web requests, redirect to a locked account page
            # (You would create this view and template)
            return redirect('accounts:account_locked')

        response = self.get_response(request)
        return response


class EmailVerificationMiddleware:
    """
    Middleware to enforce email verification for certain actions.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # URLs that require email verification
        self.verification_required_urls = [
            '/api/v1/locator/',
            '/api/v1/toolkit/',
            '/api/v1/subscriptions/subscribe/',
        ]

    def __call__(self, request):
        if (request.user.is_authenticated and 
            not request.user.email_verified and
            any(request.path.startswith(url) for url in self.verification_required_urls)):
            
            # Check if this is an API request
            if (request.path.startswith('/api/') or 
                request.META.get('HTTP_ACCEPT', '').startswith('application/json')):
                
                return JsonResponse({
                    'error': 'Email verification required',
                    'message': 'Please verify your email address to access this feature',
                    'verification_required': True
                }, status=403)

        response = self.get_response(request)
        return response


class SecurityHeadersMiddleware:
    """
    Add security headers to responses for account-related pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers for account-related pages
        if request.path.startswith('/accounts/') or request.path.startswith('/api/v1/accounts/'):
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Add CSP for account pages
            if not request.path.startswith('/api/'):
                response['Content-Security-Policy'] = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "font-src 'self'; "
                    "connect-src 'self';"
                )

        return response


class RateLimitMiddleware:
    """
    Simple rate limiting middleware for authentication endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Define rate limits for different endpoints
        self.rate_limits = {
            '/api/v1/accounts/login/': {'limit': 5, 'window': 300},  # 5 attempts per 5 minutes
            '/api/v1/accounts/register/': {'limit': 3, 'window': 3600},  # 3 attempts per hour
            '/api/v1/accounts/password/reset/': {'limit': 3, 'window': 3600},  # 3 attempts per hour
        }

    def __call__(self, request):
        # Check rate limits for specific endpoints
        if request.path in self.rate_limits and request.method == 'POST':
            if not self._check_rate_limit(request):
                if request.path.startswith('/api/'):
                    return JsonResponse({
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests. Please try again later.'
                    }, status=429)

        response = self.get_response(request)
        return response

    def _check_rate_limit(self, request):
        """Check if request is within rate limits."""
        from django.core.cache import cache
        
        ip_address = get_client_ip(request)
        cache_key = f"rate_limit_{request.path}_{ip_address}"
        
        limit_config = self.rate_limits[request.path]
        limit = limit_config['limit']
        window = limit_config['window']
        
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= limit:
            return False
        
        # Increment counter
        cache.set(cache_key, current_requests + 1, window)
        return True