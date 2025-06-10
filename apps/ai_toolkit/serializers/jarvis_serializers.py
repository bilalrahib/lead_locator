from rest_framework import serializers
from ..models import JarvisConversation


class JarvisConversationSerializer(serializers.ModelSerializer):
    """Serializer for JARVIS conversations."""
    
    conversation_type_display = serializers.CharField(source='get_conversation_type_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = JarvisConversation
        fields = [
            'id', 'user_email', 'session_id', 'user_message', 'jarvis_response',
            'conversation_type', 'conversation_type_display', 'ai_model_used',
            'response_time_ms', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'jarvis_response', 'conversation_type_display',
            'ai_model_used', 'response_time_ms', 'created_at'
        ]


class JarvisChatRequestSerializer(serializers.Serializer):
    """Serializer for JARVIS chat requests."""
    
    message = serializers.CharField(max_length=2000)
    session_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    conversation_type = serializers.ChoiceField(
        choices=JarvisConversation._meta.get_field('conversation_type').choices,
        default='general'
    )

    def validate_message(self, value):
        """Validate message content."""
        if len(value.strip()) < 1:
            raise serializers.ValidationError("Message cannot be empty.")
        
        if len(value.strip()) > 2000:
            raise serializers.ValidationError("Message is too long (max 2000 characters).")
        
        return value.strip()


class LogoGenerationRequestSerializer(serializers.Serializer):
    """Serializer for logo generation requests."""
    
    business_name = serializers.CharField(max_length=200)
    style_preferences = serializers.CharField(max_length=500, required=False, allow_blank=True)
    color_preferences = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate_business_name(self, value):
        """Validate business name."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Business name must be at least 2 characters long.")
        return value.strip()


class SocialMediaRequestSerializer(serializers.Serializer):
    """Serializer for social media content generation."""
    
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
        ('linkedin', 'LinkedIn'),
    ]
    
    CONTENT_TYPE_CHOICES = [
        ('post', 'Post'),
        ('story', 'Story'),
        ('caption', 'Caption'),
    ]
    
    platform = serializers.ChoiceField(choices=PLATFORM_CHOICES)
    content_type = serializers.ChoiceField(choices=CONTENT_TYPE_CHOICES)
    business_focus = serializers.CharField(max_length=500, required=False, allow_blank=True)
    target_audience = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate(self, attrs):
        """Cross-field validation."""
        platform = attrs.get('platform')
        content_type = attrs.get('content_type')
        
        # Instagram stories have different requirements
        if platform == 'instagram' and content_type == 'story':
            if not attrs.get('business_focus'):
                raise serializers.ValidationError({
                    'business_focus': 'Business focus is required for Instagram stories.'
                })
        
        return attrs


class JarvisResponseSerializer(serializers.Serializer):
    """Serializer for JARVIS responses."""
    
    response = serializers.CharField()
    session_id = serializers.CharField()
    conversation_id = serializers.CharField(required=False)
    conversation_type = serializers.CharField()
    response_time_ms = serializers.IntegerField(required=False)
    error = serializers.BooleanField(default=False)


class LogoGenerationResponseSerializer(serializers.Serializer):
    """Serializer for logo generation responses."""
    
    business_name = serializers.CharField()
    dall_e_prompt = serializers.CharField()
    style_suggestions = serializers.ListField(child=serializers.CharField())
    color_suggestions = serializers.ListField(child=serializers.DictField())


class SocialMediaResponseSerializer(serializers.Serializer):
    """Serializer for social media content responses."""
    
    platform = serializers.CharField()
    content_type = serializers.CharField()
    content = serializers.CharField()
    conversation_id = serializers.CharField()
    hashtag_suggestions = serializers.ListField(child=serializers.CharField())