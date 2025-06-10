from django.apps import AppConfig


class ProjectCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.project_core'
    verbose_name = 'Project Core'

    def ready(self):
        """
        Import signal handlers when the app is ready.
        """
        try:
            import apps.project_core.signals  # noqa F401
        except ImportError:
            pass