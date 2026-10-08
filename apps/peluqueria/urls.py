from django.urls import path
from . import views

app_name = 'peluqueria'

urlpatterns = [
    path('', views.panel_peluqueria, name='panel_peluqueria'),
    path('agendar/', views.panel_peluqueria, name='agendar'),
    path('buscar-mascota/', views.buscar_mascota, name='buscar_mascota'),
    path('guardar-cita/', views.guardar_cita, name='guardar_cita'),
]