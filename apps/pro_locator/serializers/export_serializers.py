from rest_framework import serializers


class ExportRequestSerializer(serializers.Serializer):
    """Serializer for export requests."""
    
    format = serializers.ChoiceField(choices=['csv', 'pdf'])
    include_notes = serializers.BooleanField(default=True)
    include_contact_info = serializers.BooleanField(default=True)
    include_ratings = serializers.BooleanField(default=True)
    status_filter = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'new', 'contacted', 'interested', 'not_interested', 'placed', 'rejected'
        ]),
        required=False,
        allow_empty=True
    )
    priority_min = serializers.IntegerField(min_value=0, max_value=100, required=False)
    use_custom_branding = serializers.BooleanField(default=True)

    def validate(self, attrs):
        """Validate export request."""
        user = self.context['request'].user
        
        # Check if PDF export is allowed (Professional users only)
        if attrs['format'] == 'pdf' and not user.subscription_status == 'PROFESSIONAL':
            raise serializers.ValidationError(
                "PDF exports with custom branding are only available for Professional plan users."
            )
        
        return attrs


class ExportResponseSerializer(serializers.Serializer):
    """Serializer for export response."""
    
    export_url = serializers.URLField()
    file_name = serializers.CharField()
    format = serializers.CharField()
    records_count = serializers.IntegerField()
    export_date = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()