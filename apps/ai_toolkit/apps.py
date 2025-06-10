from django.apps import AppConfig


class AiToolkitConfig(AppConfig):
    """
    Django app configuration for AI Toolkit.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_toolkit'
    verbose_name = 'AI Toolkit'
    
    def ready(self):
        """
        Initialize app when Django starts.
        """
        # Import signals if any (for future use)
        # import apps.ai_toolkit.signals
        pass