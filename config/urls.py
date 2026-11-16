"""
URL configuration for config project.
"""
from django.conf import settings
from django.conf.urls.static import static
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
    path('inventario/', include('apps.inventario.urls')),
    path('clinico/', include('apps.clinico.urls')),
]

# En desarrollo Django sirve los adjuntos subidos (en producción no hace nada).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
