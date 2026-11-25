"""
PB-19 / RF13 · Pantallas de la factura consolidada y de la caja.

Solo el administrador y el auxiliar facturan y ven la caja. Las reglas viven
en servicios.py; aquí solo se leen los formularios y se muestran mensajes.
"""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.directorio.models import Dueno
from apps.inventario.models import Producto, Servicio
from apps.inventario.services import disponibilidad
from apps.usuarios.permissions import rol_requerido
from config.pdf import render_pdf

from . import servicios
from .models import Factura, MovimientoCaja
from .servicios import FacturaError

ROLES_CAJA = ('administrador', 'auxiliar')
solo_caja = rol_requerido(*ROLES_CAJA)


def _fecha(texto):
    try:
        return date.fromisoformat((texto or '').strip())
    except ValueError:
        return None


def _pesos(valor):
    return '$' + f'{valor:,.0f}'.replace(',', '.')


def _al_detalle(factura, ancla=''):
    return redirect(reverse('facturacion:factura_detalle', args=[factura.pk]) + ancla)


# ---------------------------------------------------------------------------
# Facturas
# ---------------------------------------------------------------------------

@login_required
@solo_caja
def lista_facturas(request):
    g = request.GET
    desde, hasta = _fecha(g.get('desde')), _fecha(g.get('hasta'))
    estado = g.get('estado') if g.get('estado') in dict(Factura.ESTADOS) else ''
    q = (g.get('q') or '').strip()

    facturas = (Factura.objects.select_related('dueno', 'usuario')
                .annotate(fecha_ref=Coalesce('fecha', 'creada_en'), n_items=Count('items')))
    if desde:
        facturas = facturas.filter(fecha_ref__date__gte=desde)
    if hasta:
        facturas = facturas.filter(fecha_ref__date__lte=hasta)
    if estado:
        facturas = facturas.filter(estado=estado)
    if q:
        filtro = Q(dueno__nombre_completo__icontains=q) | Q(dueno__telefono__icontains=q)
        if q.lstrip('#').isdigit():
            filtro |= Q(numero=int(q.lstrip('#')))
        facturas = facturas.filter(filtro)
    facturas = facturas.order_by('-fecha_ref', '-pk')

    totales = facturas.aggregate(cobrado=Sum('total', filter=Q(estado=Factura.PAGADA)),
                                 pagadas=Count('pk', filter=Q(estado=Factura.PAGADA)),
                                 borradores=Count('pk', filter=Q(estado=Factura.BORRADOR)))
    pagina = Paginator(facturas, 20).get_page(g.get('page'))
    params = g.copy()
    params.pop('page', None)
    return render(request, 'facturacion/facturas_lista.html', {
        'pagina': pagina, 'facturas': pagina.object_list, 'totales': totales,
        'filtros': {'desde': desde, 'hasta': hasta, 'estado': estado, 'q': q},
        'hay_filtros': any([desde, hasta, estado, q]),
        'estados': Factura.ESTADOS, 'querystring': params.urlencode(),
    })


@login_required
@solo_caja
def nueva_factura(request):
    """Paso 1: buscar al propietario y abrirle un borrador."""
    if request.method == 'POST':
        dueno_id = (request.POST.get('dueno') or '').strip()
        dueno = Dueno.objects.filter(pk=int(dueno_id)).first() if dueno_id.isdigit() else None
        if dueno is None:
            messages.error(request, 'Elige un propietario de la lista.')
            return redirect('facturacion:factura_nueva')
        factura, creada = servicios.crear_borrador(dueno, request.user)
        if not creada:
            messages.info(request, f'{dueno.nombre_completo} ya tenía una factura en borrador: continúa con ella.')
        return _al_detalle(factura)

    q = (request.GET.get('q') or '').strip()
    duenos = []
    if len(q) >= 2:
        duenos = (Dueno.objects.filter(Q(nombre_completo__icontains=q) | Q(telefono__icontains=q))
                  .annotate(n_mascotas=Count('mascotas', distinct=True),
                            borradores=Count('facturas', filter=Q(facturas__estado=Factura.BORRADOR),
                                             distinct=True))
                  .order_by('nombre_completo')[:20])
    return render(request, 'facturacion/factura_nueva.html', {'q': q, 'duenos': duenos})


@login_required
@solo_caja
def detalle_factura(request, pk):
    factura = get_object_or_404(Factura.objects.select_related('dueno', 'usuario', 'creada_por', 'anulada_por'),
                                pk=pk)
    contexto = {
        'factura': factura,
        'items': factura.items.select_related('cita__mascota', 'cita_peluqueria', 'producto', 'servicio'),
        'medios_pago': Factura.MEDIOS_PAGO,
        'movimientos_caja': factura.movimientos_caja.order_by('pk'),
    }
    if factura.es_borrador:
        productos = list(Producto.objects.filter(activo=True, stock_actual__gt=0).order_by('nombre'))
        for p in productos:
            p.disponible = disponibilidad(p)[0]
        contexto.update({
            'pendientes': servicios.pendientes(factura.dueno),
            'productos': [p for p in productos if p.disponible > 0],
            'servicios_catalogo': Servicio.objects.filter(activo=True).order_by('nombre'),
        })
    return render(request, 'facturacion/factura_detalle.html', contexto)


@login_required
@solo_caja
@require_POST
def agregar_item(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    p = request.POST
    tipo = p.get('tipo')
    acciones = {
        'consulta': lambda: servicios.agregar_consulta(factura, p.get('cita'), p.get('precio')),
        'peluqueria': lambda: servicios.agregar_peluqueria(factura, p.get('cita_peluqueria')),
        'insumo': lambda: servicios.agregar_insumo(factura, p.get('movimiento')),
        'producto': lambda: servicios.agregar_producto(factura, p.get('producto'), p.get('cantidad')),
        'servicio': lambda: servicios.agregar_servicio(factura, p.get('servicio'), p.get('precio')),
    }
    if tipo not in acciones:
        messages.error(request, 'Tipo de ítem no válido.')
        return _al_detalle(factura)
    try:
        item = acciones[tipo]()
    except FacturaError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Agregado: {item.cantidad} × {item.descripcion}.')
    return _al_detalle(factura, '#items')


@login_required
@solo_caja
@require_POST
def quitar_item(request, pk, item_pk):
    factura = get_object_or_404(Factura, pk=pk)
    try:
        servicios.quitar_item(factura, item_pk)
    except FacturaError as error:
        messages.error(request, str(error))
    return _al_detalle(factura, '#items')


@login_required
@solo_caja
@require_POST
def cobrar_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    try:
        factura = servicios.cobrar(factura, medio_pago=request.POST.get('medio_pago', ''),
                                   descuento=request.POST.get('descuento') or '0', usuario=request.user)
    except FacturaError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Factura {factura.numero_display} cobrada por {_pesos(factura.total)} '
                                  f'({factura.get_medio_pago_display().lower()}). El ingreso quedó en caja.')
    return _al_detalle(factura)


@login_required
@solo_caja
@require_POST
def anular_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    try:
        factura = servicios.anular(factura, motivo=request.POST.get('motivo_anulacion'), usuario=request.user)
    except FacturaError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f'Factura {factura.numero_display} anulada. Los productos volvieron al '
                                  'inventario y el ingreso se reversó en caja.')
    return _al_detalle(factura)


@login_required
@solo_caja
@require_POST
def descartar_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    try:
        servicios.descartar_borrador(factura)
    except FacturaError as error:
        messages.error(request, str(error))
        return _al_detalle(factura)
    messages.success(request, 'Borrador descartado.')
    return redirect('facturacion:facturas')


@login_required
@solo_caja
def factura_pdf(request, pk):
    factura = get_object_or_404(Factura.objects.select_related('dueno', 'usuario'), pk=pk)
    if factura.es_borrador:
        messages.error(request, 'El comprobante se genera cuando la factura se cobra.')
        return _al_detalle(factura)
    items = list(factura.items.select_related('cita__mascota', 'cita_peluqueria',
                                              'movimiento__registro_clinico__mascota').order_by('pk'))
    return render_pdf(request, 'facturacion/factura_pdf.html', {
        'factura': factura,
        'dueno': factura.dueno,
        'items': items,
        'mascotas': sorted({m for m in (_mascota_de(i) for i in items) if m}),
    }, f'Factura_{factura.numero:05d}_{slugify(factura.dueno.nombre_completo)}')


def _mascota_de(item):
    if item.cita_id:
        return item.cita.mascota.nombre
    if item.cita_peluqueria_id:
        return item.cita_peluqueria.nombre_mascota
    if item.movimiento_id and item.movimiento.registro_clinico_id:
        return item.movimiento.registro_clinico.mascota.nombre
    return None


# ---------------------------------------------------------------------------
# Caja
# ---------------------------------------------------------------------------

@login_required
@solo_caja
def caja(request):
    hoy = timezone.localdate()
    desde = _fecha(request.GET.get('desde')) or hoy.replace(day=1)
    hasta = _fecha(request.GET.get('hasta')) or hoy
    if desde > hasta:
        desde, hasta = hasta, desde
    categoria = request.GET.get('categoria') if request.GET.get('categoria') in dict(MovimientoCaja.CATEGORIAS) \
        else ''
    return render(request, 'facturacion/caja.html', {
        'r': servicios.resumen_caja(desde, hasta, categoria),
        'desde': desde, 'hasta': hasta, 'categoria': categoria,
        'categorias': MovimientoCaja.CATEGORIAS,
    })


@login_required
@solo_caja
def registrar_gasto(request):
    hoy = timezone.localdate()
    datos = {'categoria': '', 'monto': '', 'fecha': hoy.isoformat(), 'descripcion': ''}
    if request.method == 'POST':
        datos = {k: (request.POST.get(k) or '').strip() for k in datos}
        try:
            gasto = servicios.registrar_gasto(categoria=datos['categoria'], monto=datos['monto'],
                                              fecha=_fecha(datos['fecha']), descripcion=datos['descripcion'],
                                              usuario=request.user)
        except FacturaError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f'Gasto registrado: {gasto.get_categoria_display()} por {_pesos(gasto.monto)}.')
            return redirect(f"{reverse('facturacion:caja')}?desde={gasto.fecha.replace(day=1).isoformat()}"
                            f"&hasta={max(gasto.fecha, hoy).isoformat()}")
    return render(request, 'facturacion/gasto_form.html', {
        'datos': datos, 'categorias': MovimientoCaja.CATEGORIAS_GASTO, 'hoy': hoy,
    })

