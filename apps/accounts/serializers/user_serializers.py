from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from ..models import CustomUser, UserProfile, UserActivity
import re


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    terms_accepted = serializers.BooleanField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'email', 'username', 'first_name', 'last_name', 'phone',
            'password', 'password_confirm', 'terms_accepted',
            'company_name', 'marketing_emails'
        ]

    def validate_email(self, value):
        """Validate email uniqueness and format."""
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        """Validate username uniqueness and format."""
        if CustomUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        
        # Username validation
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, hyphens, and underscores."
            )
        
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        return value.lower()

    def validate_phone(self, value):
        """Validate phone number format."""
        if value:
            # Remove all non-digits
            digits = re.sub(r'\D', '', value)
            if len(digits) < 10 or len(digits) > 15:
                raise serializers.ValidationError(
                    "Phone number must be between 10 and 15 digits."
                )
        return value

    def validate_terms_accepted(self, value):
        """Validate that terms have been accepted."""
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value

    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Password confirmation doesn't match."
            })
        
        # Validate password strength
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        return attrs

    def create(self, validated_data):
        
        """Create new user account."""
        # Remove fields that shouldn't be passed to create_user
        validated_data.pop('password_confirm')
        validated_data.pop('terms_accepted')
        
        password = validated_data.pop('password')
        
        # Create user
        user = CustomUser.objects.create_user(
            password=password,
            **validated_data
        )
        
        # Generate email verification token
        user.generate_email_verification_token()
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})
    remember_me = serializers.BooleanField(default=False)

    def validate(self, attrs):
        """Validate login credentials."""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Check if user exists
            try:
                user = CustomUser.objects.get(email__iexact=email)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({
                    'non_field_errors': ['Invalid email or password.']
                })

            # Check if account is locked
            if user.is_account_locked:
                raise serializers.ValidationError({
                    'non_field_errors': ['Account is temporarily locked due to failed login attempts.']
                })

            # Check if account is active
            if not user.is_active:
                raise serializers.ValidationError({
                    'non_field_errors': ['Account is disabled.']
                })

            # Authenticate user
            user = authenticate(email=email, password=password)
            if user:
                # Reset failed attempts on successful login
                user.reset_failed_attempts()
                attrs['user'] = user
            else:
                # Increment failed attempts
                user.increment_failed_attempts()
                raise serializers.ValidationError({
                    'non_field_errors': ['Invalid email or password.']
                })
        else:
            raise serializers.ValidationError({
                'non_field_errors': ['Must include email and password.']
            })

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile (read-only)."""
    
    full_name = serializers.ReadOnlyField()
    subscription_status = serializers.ReadOnlyField()
    is_premium_user = serializers.ReadOnlyField()
    profile_completion = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone', 'company_name', 'website', 'bio', 'avatar',
            'email_verified', 'subscription_status', 'is_premium_user',
            'email_notifications', 'marketing_emails', 'timezone_preference',
            'date_joined', 'last_login', 'last_activity', 'profile_completion'
        ]
        read_only_fields = [
            'id', 'email', 'username', 'email_verified', 'subscription_status',
            'is_premium_user', 'date_joined', 'last_login', 'last_activity'
        ]

    def get_profile_completion(self, obj):
        """Get profile completion percentage."""
        try:
            return obj.profile.completion_percentage
        except:
            return 0


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'phone', 'company_name', 'website', 'bio',
            'avatar', 'email_notifications', 'marketing_emails', 'timezone_preference'
        ]

    def validate_phone(self, value):
        """Validate phone number format."""
        if value:
            digits = re.sub(r'\D', '', value)
            if len(digits) < 10 or len(digits) > 15:
                raise serializers.ValidationError(
                    "Phone number must be between 10 and 15 digits."
                )
        return value

    def validate_avatar(self, value):
        """Validate avatar image."""
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Avatar image must be smaller than 5MB.")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Avatar must be a JPEG, PNG, GIF, or WebP image."
                )
        
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing password."""
    
    current_password = serializers.CharField(style={'input_type': 'password'})
    new_password = serializers.CharField(
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(style={'input_type': 'password'})

    def validate_current_password(self, value):
        """Validate current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        """Validate new password confirmation."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New password confirmation doesn't match."
            })
        
        # Validate password strength
        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})
        
        return attrs

    def save(self):
        """Change user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate that user with email exists."""
        if not CustomUser.objects.filter(email__iexact=value).exists():
            # Don't reveal whether email exists or not for security
            pass
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    
    token = serializers.CharField()
    new_password = serializers.CharField(
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        """Validate token and password confirmation."""
        token = attrs['token']
        
        # Find user with this token
        try:
            user = CustomUser.objects.get(password_reset_token=token)
            if not user.verify_password_reset_token(token):
                raise serializers.ValidationError({
                    'token': 'Invalid or expired token.'
                })
            attrs['user'] = user
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                'token': 'Invalid or expired token.'
            })

        # Validate password confirmation
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Password confirmation doesn't match."
            })
        
        # Validate password strength
        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})
        
        return attrs

    def save(self):
        """Reset user password."""
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.clear_password_reset_token()
        user.save()
        return user


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""
    
    token = serializers.CharField()

    def validate_token(self, value):
        """Validate verification token."""
        try:
            user = CustomUser.objects.get(email_verification_token=value)
            if not user.verify_email(value):
                raise serializers.ValidationError("Invalid or expired verification token.")
            return value
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired verification token.")


class EmailChangeSerializer(serializers.Serializer):
    """Serializer for changing email address."""
    
    new_email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate_new_email(self, value):
        """Validate new email."""
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        """Validate current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")
        return value

    def save(self):
        """Change user email."""
        user = self.context['request'].user
        user.email = self.validated_data['new_email']
        user.email_verified = False  # Require re-verification
        user.generate_email_verification_token()
        user.save()
        return user


class UserDeleteSerializer(serializers.Serializer):
    """Serializer for account deletion."""
    
    password = serializers.CharField(style={'input_type': 'password'})
    confirmation = serializers.CharField()

    def validate_password(self, value):
        """Validate current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")
        return value

    def validate_confirmation(self, value):
        """Validate deletion confirmation."""
        if value.lower() != 'delete my account':
            raise serializers.ValidationError(
                "Please type 'DELETE MY ACCOUNT' to confirm account deletion."
            )
        return value

    def save(self):
        """Delete user account."""
        user = self.context['request'].user
        user.is_active = False
        user.email = f"deleted_{user.id}@deleted.com"
        user.save()
        return user