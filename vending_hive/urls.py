from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Include project_core URLs (both API and web)
    path('', include('apps.project_core.urls')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.subscriptions.urls')),  # Add this line
    path('', include('apps.locator.urls')),  # Add this line
    path('', include('apps.ai_toolkit.urls')), #Add this line
    path('', include('apps.affiliates.urls')),  # Add this line
    path('', include('apps.pro_locator.urls')),  # Add this line
    path('', include('apps.operations.urls')),  # Add this lines

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "Vending Hive Administration"
admin.site.site_title = "Vending Hive Admin"
admin.site.index_title = "Welcome to Vending Hive Administration"