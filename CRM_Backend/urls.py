from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('company_details/', include('company_details.urls')),
    path('leads/', include('leads.urls')),
    path('categories/', include('categories.urls')),
    path('tasks/', include('tasks.urls')),
    path('campaigns/', include('campaigns.urls')),
    path('reports/', include('reports.urls')),  
    path('invoice/', include('invoice.urls')),
    path('notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)