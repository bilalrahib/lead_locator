from django.apps import AppConfig


class ProLocatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pro_locator'
    verbose_name = 'Pro Locator'

    def ready(self):
        """Import signal handlers when the app is ready."""
        try:
            import apps.pro_locator.signals  # noqa F401
        except ImportError:
            pass