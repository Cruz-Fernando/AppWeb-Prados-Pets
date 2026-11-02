from django.urls import path
from . import views

app_name = 'clinico'

urlpatterns = [
    # Historia clínica
    path('historial/', views.seleccionar_mascota_historial, name='seleccionar_mascota_historial'),
    path('mascota/<int:mascota_id>/historial/', views.historial_clinico, name='historial_clinico'),
    path('mascota/<int:mascota_id>/historial/pdf/', views.historia_pdf, name='historia_pdf'),
    path('mascota/<int:mascota_id>/registro/<slug:tipo>/', views.nuevo_registro, name='nuevo_registro'),
    path('registro/<int:pk>/', views.registro_detalle, name='registro_detalle'),
    path('registro/<int:pk>/editar/', views.editar_registro, name='editar_registro'),
    path('registro/<int:pk>/anular/', views.anular_registro, name='anular_registro'),
    path('registro/<int:pk>/pdf/', views.registro_pdf, name='registro_pdf'),

    # Hospitalización
    path('hospitalizacion/', views.hospitalizacion_lista, name='hospitalizacion'),
    path('hospitalizacion/ingresar/', views.ingresar_paciente, name='ingresar_paciente'),
    path('hospitalizacion/<int:pk>/', views.hospitalizacion_detalle, name='hospitalizacion_detalle'),
    path('hospitalizacion/<int:pk>/alta/', views.dar_alta, name='dar_alta'),
    path('hospitalizacion/<int:pk>/pdf/', views.hospitalizacion_pdf, name='hospitalizacion_pdf'),

    # Recordatorios (la vista existía pero faltaba la ruta)
    path('recordatorios/', views.recordatorios, name='recordatorios'),
]
