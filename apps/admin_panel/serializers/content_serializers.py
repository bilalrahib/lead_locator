from rest_framework import serializers
from ..models import ContentTemplate, SystemSettings, AdminLog


class ContentTemplateSerializer(serializers.ModelSerializer):
    """Serializer for content templates."""
    
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    tag_list = serializers.ReadOnlyField()

    class Meta:
        model = ContentTemplate
        fields = [
            'id', 'name', 'template_type', 'title', 'content', 'preview_url',
            'thumbnail', 'description', 'tags', 'tag_list', 'status',
            'is_featured', 'usage_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_by', 'created_at', 'updated_at']


class ContentTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating content templates."""
    
    class Meta:
        model = ContentTemplate
        fields = [
            'name', 'template_type', 'title', 'content', 'preview_url',
            'thumbnail', 'description', 'tags', 'status', 'is_featured'
        ]

    def validate_name(self, value):
        """Validate template name uniqueness."""
        if ContentTemplate.objects.filter(name=value).exists():
            raise serializers.ValidationError("Template with this name already exists.")
        return value

    def create(self, validated_data):
        """Create template with current user as creator."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class SystemSettingsSerializer(serializers.ModelSerializer):
    """Serializer for system settings."""
    
    typed_value = serializers.SerializerMethodField()
    updated_by_name = serializers.CharField(source='updated_by.full_name', read_only=True)

    class Meta:
        model = SystemSettings
        fields = [
            'id', 'key', 'value', 'typed_value', 'setting_type', 'description',
            'category', 'is_active', 'is_editable', 'updated_by',
            'updated_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'updated_by']

    def get_typed_value(self, obj):
        """Get value with proper type conversion."""
        return obj.get_typed_value()

    def update(self, instance, validated_data):
        """Update with current user tracking."""
        validated_data['updated_by'] = self.context['request'].user
        return super().update(instance, validated_data)


class AdminLogSerializer(serializers.ModelSerializer):
    """Serializer for admin logs."""
    
    admin_user_name = serializers.CharField(source='admin_user.full_name', read_only=True)
    target_user_name = serializers.CharField(source='target_user.full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_type_display', read_only=True)

    class Meta:
        model = AdminLog
        fields = [
            'id', 'admin_user', 'admin_user_name', 'action_type', 'action_display',
            'target_user', 'target_user_name', 'description', 'before_state',
            'after_state', 'ip_address', 'created_at'
        ]
        read_only_fields = fields