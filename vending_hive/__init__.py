# This will make Django load up Celery worker when it starts
from .celery import app as celery_app

__all__ = ('celery_app',)