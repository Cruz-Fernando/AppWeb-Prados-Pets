"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='usuarios:dashboard'), name='home'),
    path('', include('apps.usuarios.urls')),
    path('directorio/', include('apps.directorio.urls')),
    path('peluqueria/', include('apps.peluqueria.urls')),
    path('agendamiento/', include('apps.agendamiento.urls')),
]
