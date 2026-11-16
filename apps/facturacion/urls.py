from django.urls import path

from . import views

app_name = 'facturacion'

urlpatterns = [
    path('', views.panel, name='panel'),
    path('servicio/<int:pk>/cerrar/', views.cerrar_servicio, name='cerrar_servicio'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),
]