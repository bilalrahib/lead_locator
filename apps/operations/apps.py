from django.apps import AppConfig


class OperationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.operations'
    verbose_name = 'Operations'

    def ready(self):
        """Import signal handlers when the app is ready."""
        try:
            import apps.operations.signals  # noqa F401
        except ImportError:
            pass