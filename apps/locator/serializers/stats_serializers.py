from rest_framework import serializers


class LocationStatsSerializer(serializers.Serializer):
    """Serializer for location search statistics."""
    
    total_searches = serializers.IntegerField()
    total_locations_found = serializers.IntegerField()
    searches_this_month = serializers.IntegerField()
    locations_this_month = serializers.IntegerField()
    favorite_machine_type = serializers.CharField()
    average_results_per_search = serializers.FloatField()
    top_zip_codes = serializers.ListField()
    excluded_locations_count = serializers.IntegerField()


class ExportRequestSerializer(serializers.Serializer):
    """Serializer for export requests."""
    
    format = serializers.ChoiceField(choices=['csv', 'xlsx', 'docx'])
    include_notes = serializers.BooleanField(default=True)
    include_maps_links = serializers.BooleanField(default=True)