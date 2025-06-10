from .base import *

DEBUG = True

INSTALLED_APPS += [
    'django_extensions',
]
# Add to ALLOWED_HOSTS
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'testserver',  # Add this for testing
    '0.0.0.0',
]
# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Database for development - you can use SQLite for quick testing
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }