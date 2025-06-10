from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.subscriptions'
    verbose_name = 'Subscriptions'

    def ready(self):
        """Import signal handlers when the app is ready."""
        try:
            import apps.subscriptions.signals  # noqa F401
        except ImportError:
            pass