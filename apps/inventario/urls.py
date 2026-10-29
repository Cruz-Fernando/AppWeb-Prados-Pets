from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('cargar-excel/', views.cargar_catalogo_excel, name='cargar_excel'),
]