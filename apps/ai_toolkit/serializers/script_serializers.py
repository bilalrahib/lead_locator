from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import GeneratedScript, ScriptTemplate

User = get_user_model()


class GeneratedScriptSerializer(serializers.ModelSerializer):
    """Serializer for generated scripts."""
    
    script_type_display = serializers.CharField(source='get_script_type_display', read_only=True)
    machine_type_display = serializers.CharField(source='get_target_machine_type_display', read_only=True)
    can_regenerate = serializers.ReadOnlyField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = GeneratedScript
        fields = [
            'id', 'user_email', 'script_type', 'script_type_display',
            'target_location_name', 'target_location_category', 
            'target_machine_type', 'machine_type_display', 'script_content',
            'is_template', 'regeneration_count', 'ai_model_used',
            'can_regenerate', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'script_type_display', 'machine_type_display',
            'is_template', 'regeneration_count', 'ai_model_used', 'can_regenerate',
            'created_at', 'updated_at'
        ]


class ScriptGenerationRequestSerializer(serializers.Serializer):
    """Serializer for script generation requests."""
    
    script_type = serializers.ChoiceField(choices=GeneratedScript.SCRIPT_TYPE_CHOICES)
    target_location_name = serializers.CharField(max_length=255)
    target_location_category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    target_machine_type = serializers.ChoiceField(choices=GeneratedScript.MACHINE_TYPE_CHOICES)
    custom_requirements = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate_target_location_name(self, value):
        """Validate location name."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Location name must be at least 2 characters long.")
        return value.strip()

    def validate_custom_requirements(self, value):
        """Validate custom requirements."""
        if value and len(value.strip()) > 1000:
            raise serializers.ValidationError("Custom requirements must be less than 1000 characters.")
        return value.strip() if value else ""


class ScriptRegenerationRequestSerializer(serializers.Serializer):
    """Serializer for script regeneration requests."""
    
    script_id = serializers.UUIDField()
    custom_requirements = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate_script_id(self, value):
        """Validate that script exists and belongs to user."""
        try:
            script = GeneratedScript.objects.get(id=value)
            user = self.context['request'].user
            
            if script.user != user:
                raise serializers.ValidationError("Script not found or access denied.")
            
            if not script.can_regenerate:
                raise serializers.ValidationError("Script regeneration not allowed for your subscription plan.")
            
            return value
        except GeneratedScript.DoesNotExist:
            raise serializers.ValidationError("Script not found.")


class ScriptTemplateSerializer(serializers.ModelSerializer):
    """Serializer for script templates."""
    
    script_type_display = serializers.CharField(source='get_script_type_display', read_only=True)
    machine_type_display = serializers.CharField(source='get_machine_type_display', read_only=True)
    can_access = serializers.SerializerMethodField()

    class Meta:
        model = ScriptTemplate
        fields = [
            'id', 'name', 'script_type', 'script_type_display',
            'machine_type', 'machine_type_display', 'location_category',
            'content', 'is_premium', 'usage_count', 'can_access'
        ]
        read_only_fields = ['id', 'usage_count']

    def get_can_access(self, obj):
        """Check if current user can access this template."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_access(request.user)
        return False


class TemplateUsageRequestSerializer(serializers.Serializer):
    """Serializer for using a template."""
    
    template_id = serializers.UUIDField()
    target_location_name = serializers.CharField(max_length=255)
    target_location_category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    target_machine_type = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_template_id(self, value):
        """Validate template exists and user can access it."""
        try:
            template = ScriptTemplate.objects.get(id=value, is_active=True)
            user = self.context['request'].user
            
            if not template.can_access(user):
                raise serializers.ValidationError("Template access not allowed for your subscription plan.")
            
            return value
        except ScriptTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found or inactive.")