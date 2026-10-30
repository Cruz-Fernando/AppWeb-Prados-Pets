from django.urls import path
from . import views

urlpatterns = [
    path('registrar-dueno/', views.registrar_dueno, name='registrar_dueno'),
    path('duenos/<int:dueno_id>/editar/', views.editar_dueno, name='editar_dueno'),
    path('duenos/lista/', views.lista_duenos, name='lista_duenos'),
    path('duenos/exportar-excel/', views.exportar_duenos_excel, name='exportar_duenos_excel'),
    
    path('mascotas/registrar/', views.registrar_mascota, name='registrar_mascota'),
    path('mascotas/<int:mascota_id>/editar/', views.editar_mascota, name='editar_mascota'),
    path('mascotas/lista/', views.lista_mascotas, name='lista_mascotas'),
    path('mascotas/exportar-excel/', views.exportar_mascotas_excel, name='exportar_mascotas_excel'),

    path('buscar/', views.buscar_directorio, name='buscar_directorio'),
    path('exportar-excel/', views.exportar_directorio_excel, name='exportar_directorio_excel'),
    path('autocomplete-duenos/', views.autocomplete_duenos, name='autocomplete_duenos'),
]