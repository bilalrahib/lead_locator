from django.http import JsonResponse
from django.urls import resolve
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class OperationsPermissionsMiddleware:
    """
    Middleware to check operations-specific permissions.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this is an operations API request
        if request.path.startswith('/api/v1/operations/'):
            # Ensure user is authenticated for all operations endpoints
            if not request.user.is_authenticated:
                return JsonResponse({
                    'error': 'Authentication required for operations access'
                }, status=401)
            
            # Check if user has an active subscription for certain endpoints
            if self._requires_active_subscription(request.path):
                if not self._has_active_subscription(request.user):
                    return JsonResponse({
                        'error': 'Active subscription required for this feature'
                    }, status=403)
        
        response = self.get_response(request)
        return response

    def _requires_active_subscription(self, path):
        """Check if the endpoint requires an active subscription."""
        # For now, all operations features require a subscription
        # This can be customized based on your business logic
        return True

    def _has_active_subscription(self, user):
        """Check if user has an active subscription."""
        try:
            return (hasattr(user, 'subscription') and 
                   user.subscription and 
                   user.subscription.is_active and 
                   not user.subscription.is_expired)
        except Exception as e:
            logger.error(f"Error checking subscription for user {user.id}: {e}")
            return False    