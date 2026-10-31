from django.urls import path
from . import views

app_name = 'clinico'

urlpatterns = [
    path('hospitalizacion/', views.hospitalizacion_lista, name='hospitalizacion'),
    path('hospitalizacion/ingresar/', views.ingresar_paciente, name='ingresar_paciente'),
]