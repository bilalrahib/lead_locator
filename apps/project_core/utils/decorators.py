import time
import functools
import logging
from typing import Callable, Any
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def log_execution_time(func: Callable) -> Callable:
    """
    Decorator to log function execution time.
    
    Args:
        func: Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(
            f"Function '{func.__name__}' executed in {execution_time:.4f} seconds"
        )
        
        return result
    
    return wrapper


def require_subscription(allowed_plans: list = None):
    """
    Decorator to require specific subscription plans.
    
    Args:
        allowed_plans: List of allowed plan names
        
    Returns:
        Callable: Decorator function
    """
    if allowed_plans is None:
        allowed_plans = ['STARTER', 'PRO', 'ELITE', 'PROFESSIONAL']
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if hasattr(request, 'resolver_match') and 'api' in request.resolver_match.namespace:
                    return JsonResponse(
                        {'error': 'Authentication required'}, 
                        status=401
                    )
                return redirect('login')
            
            # Check if user has valid subscription
            try:
                from apps.subscriptions.models import UserSubscription
                subscription = UserSubscription.objects.get(
                    user=request.user,
                    is_active=True
                )
                
                if subscription.plan.name not in allowed_plans:
                    if hasattr(request, 'resolver_match') and 'api' in request.resolver_match.namespace:
                        return JsonResponse(
                            {'error': 'Subscription upgrade required'}, 
                            status=403
                        )
                    raise PermissionDenied("Subscription upgrade required")
                    
            except UserSubscription.DoesNotExist:
                if hasattr(request, 'resolver_match') and 'api' in request.resolver_match.namespace:
                    return JsonResponse(
                        {'error': 'Active subscription required'}, 
                        status=403
                    )
                raise PermissionDenied("Active subscription required")
            
            return func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


def rate_limit(max_requests: int = 60, window_minutes: int = 1):
    """
    Simple rate limiting decorator.
    
    Args:
        max_requests: Maximum requests allowed
        window_minutes: Time window in minutes
        
    Returns:
        Callable: Decorator function
    """
    from django.core.cache import cache
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get client IP
            from apps.project_core.utils.helpers import get_client_ip
            client_ip = get_client_ip(request)
            
            # Create cache key
            cache_key = f"rate_limit_{client_ip}_{func.__name__}"
            
            # Get current request count
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= max_requests:
                if hasattr(request, 'resolver_match') and 'api' in request.resolver_match.namespace:
                    return JsonResponse(
                        {'error': 'Rate limit exceeded'}, 
                        status=429
                    )
                return HttpResponse('Rate limit exceeded', status=429)
            
            # Increment counter
            cache.set(cache_key, current_requests + 1, window_minutes * 60)
            
            return func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


def handle_exceptions(default_response: Any = None):
    """
    Decorator to handle exceptions gracefully.
    
    Args:
        default_response: Default response on exception
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Exception in {func.__name__}: {e}")
                
                # Check if this is an API view
                if args and hasattr(args[0], 'META'):
                    request = args[0]
                    if hasattr(request, 'resolver_match') and 'api' in str(request.resolver_match):
                        return JsonResponse(
                            {'error': 'An error occurred'}, 
                            status=500
                        )
                
                if default_response is not None:
                    return default_response
                
                raise
        
        return wrapper
    
    return decorator


def cache_response(timeout: int = 300):
    """
    Decorator to cache view responses.
    
    Args:
        timeout: Cache timeout in seconds
        
    Returns:
        Callable: Decorator function
    """
    from django.core.cache import cache
    from django.utils.cache import get_cache_key
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            # Create cache key based on request
            cache_key = f"view_cache_{func.__name__}_{hash(str(request.GET))}"
            
            # Try to get cached response
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Generate response and cache it
            response = func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)
            
            return response
        
        return wrapper
    
    return decorator


def admin_required(func: Callable) -> Callable:
    """
    Decorator to require admin/staff privileges.
    
    Args:
        func: Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @functools.wraps(func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            if hasattr(request, 'resolver_match') and 'api' in str(request.resolver_match):
                return JsonResponse(
                    {'error': 'Admin privileges required'}, 
                    status=403
                )
            raise PermissionDenied("Admin privileges required")
        
        return func(request, *args, **kwargs)
    
    return wrapper


def api_key_required(func: Callable) -> Callable:
    """
    Decorator to require API key authentication.
    
    Args:
        func: Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        api_key = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')
        
        if not api_key:
            return JsonResponse(
                {'error': 'API key required'}, 
                status=401
            )
        
        # Validate API key (you'd implement your own validation logic)
        valid_api_keys = getattr(settings, 'VALID_API_KEYS', [])
        
        if api_key not in valid_api_keys:
            return JsonResponse(
                {'error': 'Invalid API key'}, 
                status=401
            )
        
        return func(request, *args, **kwargs)
    
    return wrapper