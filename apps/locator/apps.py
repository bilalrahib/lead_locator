from django.apps import AppConfig


class LocatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.locator'
    verbose_name = 'Locator'

    def ready(self):
        """Import signal handlers when the app is ready."""
        try:
            import apps.locator.signals  # noqa F401
        except ImportError:
            pass