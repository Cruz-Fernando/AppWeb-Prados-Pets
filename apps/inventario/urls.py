from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.InventarioListView.as_view(), name='lista'),
    path('nuevo/', views.ProductoCreateView.as_view(), name='crear_producto'),
    path('reposicion/', views.registrar_reposicion, name='reposicion'),
    path('cargar-excel/', views.cargar_catalogo_excel, name='cargar_excel'),
    path('exportar-excel/', views.exportar_inventario_excel, name='exportar_excel'),
    path('descargar-plantilla/', views.descargar_plantilla_excel, name='descargar_plantilla'),
    path('kardex/', views.KardexListView.as_view(), name='kardex'),
]