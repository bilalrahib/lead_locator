from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class EmailBackend(BaseBackend):
    """
    Custom authentication backend that allows users to login with email.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate user with email and password.
        
        Args:
            request: HTTP request object
            email: User's email address
            password: User's password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        if email is None or password is None:
            return None

        try:
            # Find user by email (case insensitive)
            user = User.objects.get(Q(email__iexact=email))
            
            # Check password
            if user.check_password(password):
                return user
                
        except User.DoesNotExist:
            # Run default password hasher to prevent timing attacks
            User().set_password(password)
            return None
        
        return None

    def get_user(self, user_id):
        """
        Get user by ID.
        
        Args:
            user_id: User's primary key
            
        Returns:
            User object if found, None otherwise
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class UsernameOrEmailBackend(BaseBackend):
    """
    Authentication backend that allows login with either username or email.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with username/email and password.
        
        Args:
            request: HTTP request object
            username: User's username or email
            password: User's password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        if username is None or password is None:
            return None

        try:
            # Try to find user by email first, then username
            user = User.objects.get(
                Q(email__iexact=username) | Q(username__iexact=username)
            )
            
            # Check password
            if user.check_password(password):
                return user
                
        except User.DoesNotExist:
            # Run default password hasher to prevent timing attacks
            User().set_password(password)
            return None
        
        return None

    def get_user(self, user_id):
        """Get user by ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None