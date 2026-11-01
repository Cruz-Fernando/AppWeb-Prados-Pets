from django.urls import path
from . import views

app_name = 'clinico'

urlpatterns = [
    path('historial/', views.seleccionar_mascota_historial, name='seleccionar_mascota_historial'),
    path('mascota/<int:mascota_id>/historial/', views.historial_clinico, name='historial_clinico'),
    path('hospitalizacion/', views.hospitalizacion_lista, name='hospitalizacion'),
    path('hospitalizacion/ingresar/', views.ingresar_paciente, name='ingresar_paciente'),
]