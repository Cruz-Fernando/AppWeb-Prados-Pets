from django.urls import path

from . import views

app_name = "agendamiento"

urlpatterns = [
    path("calendario/", views.calendario, name="calendario"),
    path("agendar/", views.agendar_cita, name="agendar_cita"),
    path("buscar-mascotas/", views.buscar_mascotas_ajax, name="buscar_mascotas_ajax"),
    path("cita/<int:pk>/pdf/", views.cita_pdf, name="cita_pdf"),
]
