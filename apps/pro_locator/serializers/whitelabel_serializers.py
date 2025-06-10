from rest_framework import serializers
from ..models import WhiteLabelSettings


class WhiteLabelSettingsSerializer(serializers.ModelSerializer):
    """Serializer for white label settings."""
    
    has_custom_branding = serializers.ReadOnlyField()

    class Meta:
        model = WhiteLabelSettings
        fields = [
            'id', 'company_name', 'company_logo', 'primary_color', 'secondary_color',
            'company_website', 'company_phone', 'company_email', 'custom_domain',
            'remove_vending_hive_branding', 'is_active', 'has_custom_branding',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'has_custom_branding', 'created_at', 'updated_at']


class WhiteLabelSettingsUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating white label settings."""

    class Meta:
        model = WhiteLabelSettings
        fields = [
            'company_name', 'company_logo', 'primary_color', 'secondary_color',
            'company_website', 'company_phone', 'company_email', 'custom_domain',
            'remove_vending_hive_branding', 'is_active'
        ]

    def validate_primary_color(self, value):
        """Validate hex color format."""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError("Color must be in hex format (#RRGGBB).")
        return value

    def validate_secondary_color(self, value):
        """Validate hex color format."""
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError("Color must be in hex format (#RRGGBB).")
        return value

    def validate_company_logo(self, value):
        """Validate uploaded logo."""
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Logo file must be smaller than 5MB.")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/svg+xml']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Logo must be a JPEG, PNG, or SVG image."
                )
        
        return value

    def validate(self, attrs):
        """Validate that user has Professional subscription for white-labeling."""
        user = self.context['request'].user
        
        if user.subscription_status != 'PROFESSIONAL':
            raise serializers.ValidationError(
                "White-label features are only available for Professional plan users."
            )
        
        return attrs