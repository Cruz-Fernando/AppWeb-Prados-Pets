from django.urls import path

from . import views, views_facturas as fac

app_name = 'facturacion'

urlpatterns = [
    # Ganancias por groomer (comisión del 40 %)
    path('', views.panel, name='panel'),
    path('servicio/<int:pk>/cerrar/', views.cerrar_servicio, name='cerrar_servicio'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),

    # PB-19: factura consolidada
    path('facturas/', fac.lista_facturas, name='facturas'),
    path('facturas/nueva/', fac.nueva_factura, name='factura_nueva'),
    path('facturas/<int:pk>/', fac.detalle_factura, name='factura_detalle'),
    path('facturas/<int:pk>/agregar/', fac.agregar_item, name='factura_agregar'),
    path('facturas/<int:pk>/item/<int:item_pk>/quitar/', fac.quitar_item, name='factura_quitar'),
    path('facturas/<int:pk>/cobrar/', fac.cobrar_factura, name='factura_cobrar'),
    path('facturas/<int:pk>/anular/', fac.anular_factura, name='factura_anular'),
    path('facturas/<int:pk>/descartar/', fac.descartar_factura, name='factura_descartar'),
    path('facturas/<int:pk>/pdf/', fac.factura_pdf, name='factura_pdf'),

    # PB-19: caja (ingresos y gastos)
    path('caja/', fac.caja, name='caja'),
    path('caja/gasto/', fac.registrar_gasto, name='gasto'),
]
