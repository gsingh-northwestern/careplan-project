"""
Root URL configuration for the Care Plan Generator project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('careplan.urls')),
]
