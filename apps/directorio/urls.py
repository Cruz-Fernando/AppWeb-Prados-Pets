from django.urls import path
from . import views

urlpatterns = [
    path('registrar-dueno/', views.registrar_dueno, name='registrar_dueno'),
    path('mascotas/registrar/', views.registrar_mascota, name='registrar_mascota'),
    path('duenos/autocomplete/', views.autocomplete_duenos, name='autocomplete_duenos'),
    path('buscar/', views.buscar_directorio, name='buscar_directorio'),
]
