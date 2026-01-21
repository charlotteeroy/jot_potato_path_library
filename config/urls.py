"""
URL configuration for Jot Potato Path Library.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('paths.urls')),
]
