from django.urls import path
from . import views

app_name = 'peluqueria'

urlpatterns = [
    path('', views.panel_peluqueria, name='panel_peluqueria'),
    path('agendar/', views.panel_peluqueria, name='agendar'),
    path('buscar-mascota/', views.buscar_mascota, name='buscar_mascota'),
    path('guardar-cita/', views.guardar_cita, name='guardar_cita'),
    path('comprobante/<int:pk>/', views.comprobante_pdf, name='comprobante_pdf'),
    path('cita/<int:pk>/cancelar/', views.cancelar_cita, name='cancelar_cita'),
    # Confirmación para el cliente: enlace firmado que se envía por WhatsApp (sin iniciar sesión)
    path('confirmacion/<str:token>/', views.confirmacion_cliente, name='confirmacion_cliente'),
]