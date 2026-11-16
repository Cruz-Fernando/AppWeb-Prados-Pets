from datetime import datetime
from urllib.parse import urlencode
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, models
from django.contrib.staticfiles import finders
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView

from apps.usuarios.permissions import rol_requerido
from .carga_excel import procesar_catalogo
from .forms import ProductoForm, ReposicionForm, CargaExcelForm, SalidaManualForm, RetirarProductoForm
from .models import Producto, Medicamento, Servicio, MovimientoInventario, CategoriaProducto, InsumoServicio
from .services import (
    StockInsuficiente,
    avisos_stock_bajo,
    disponibilidad,
    registrar_entrada,
    registrar_salida_manual,
    retirar_producto,
)

# Mismos roles que ven el módulo en el menú lateral. Antes bastaba con iniciar
# sesión: un groomer o un domiciliario podía crear productos y mover stock
# escribiendo la dirección a mano.
ROLES_INVENTARIO = ('administrador', 'veterinario', 'auxiliar')
solo_inventario = method_decorator(rol_requerido(*ROLES_INVENTARIO), name='dispatch')


@solo_inventario
class InventarioListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'inventario/inventario_list.html'
    context_object_name = 'productos'
    paginate_by = 15

    def ver_retirados(self):
        return self.request.GET.get('retirados') == '1'

    def get_template_names(self):
        # La búsqueda en vivo solo pide la tabla, no la página entera
        if self.request.GET.get('parcial') == '1':
            return ['inventario/_tabla_productos.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = (Producto.objects.filter(activo=not self.ver_retirados())
                    .select_related('categoria', 'proveedor', 'medicamento')
                    .order_by('nombre', 'pk'))
        q = (self.request.GET.get('q') or '').strip()
        categoria_id = self.request.GET.get('categoria')

        if q:
            queryset = queryset.filter(
                models.Q(nombre__icontains=q) |
                models.Q(codigo__icontains=q) |
                models.Q(codigo_barras__icontains=q)
            )
        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CategoriaProducto.objects.all()
        productos = Producto.objects.filter(activo=True)
        context['total_valor_inventario'] = sum(p.valor_total_inventario for p in productos)
        context['productos_bajo_stock'] = productos.filter(stock_actual__lte=models.F('stock_minimo')).count()
        context['total_retirados'] = Producto.objects.filter(activo=False).count()
        context['ver_retirados'] = self.ver_retirados()
        context['q'] = (self.request.GET.get('q') or '').strip()
        context['productos_vencidos'] = productos.filter(
            stock_actual__gt=0, fecha_vencimiento__lt=timezone.localdate()).count()
        return context


@solo_inventario
class ProductoCreateView(LoginRequiredMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'inventario/producto_form.html'
    success_url = reverse_lazy('inventario:lista')

    def form_valid(self, form):
        with transaction.atomic():
            producto = form.save()
            if producto.stock_actual > 0:
                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo='ENTRADA_COMPRA',
                    cantidad=producto.stock_actual,
                    precio_unitario_historico=producto.precio_compra,
                    monto_total=producto.stock_actual * producto.precio_compra,
                    usuario=self.request.user,
                    observacion='Inventario Inicial / Registro de Producto'
                )
        messages.success(self.request, "Producto creado exitosamente con su movimiento contable inicial.")
        return redirect(self.success_url)


def _producto_de_la_url(request, solo_activos=True):
    producto_id = (request.GET.get('producto') or request.POST.get('producto') or '').strip()
    if not producto_id.isdigit():
        return None
    filtro = {'activo': True} if solo_activos else {}
    return Producto.objects.filter(pk=int(producto_id), **filtro).first()


@login_required
@rol_requerido(*ROLES_INVENTARIO)
def registrar_reposicion(request):
    """Añadir unidades a un producto (compra o reposición)."""
    producto = _producto_de_la_url(request)
    if request.method == 'POST':
        form = ReposicionForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            producto = datos['producto']
            registrar_entrada(
                producto.pk, datos['cantidad'], usuario=request.user,
                costo=datos.get('nuevo_precio_compra'),
                fecha_vencimiento=datos.get('fecha_vencimiento'),
                nota=datos.get('observacion') or '',
            )
            producto.refresh_from_db()
            messages.success(request, f"Se añadieron {datos['cantidad']} unidades a «{producto.nombre}». "
                                      f"Stock actual: {producto.stock_actual}.")
            return redirect(_volver_a_lista(request))
    else:
        form = ReposicionForm(initial={'producto': producto} if producto else None)

    return render(request, 'inventario/reposicion_form.html', {
        'form': form, 'producto': producto, 'volver': _volver_a_lista(request),
    })


def _volver_a_lista(request):
    """Vuelve a la lista con la misma búsqueda que tenía el usuario."""
    q = (request.GET.get('q') or request.POST.get('q') or '').strip()
    destino = reverse('inventario:lista')
    return f"{destino}?{urlencode({'q': q})}" if q else destino


@login_required
@rol_requerido(*ROLES_INVENTARIO)
def registrar_salida(request):
    """Quitar unidades a mano, con su motivo (uso interno, vencimiento, daño, pérdida, venta...)."""
    producto = _producto_de_la_url(request)
    if producto is None:
        productos = Producto.objects.filter(activo=True, stock_actual__gt=0).order_by('nombre')
        return render(request, 'inventario/salida_form.html', {
            'productos': productos, 'volver': _volver_a_lista(request),
        })

    form = SalidaManualForm(request.POST or None, producto=producto)
    if request.method == 'POST' and form.is_valid():
        datos = form.cleaned_data
        try:
            movimiento = registrar_salida_manual(
                producto.pk, datos['cantidad'], motivo=datos['motivo'], usuario=request.user,
                nota=datos.get('observacion') or '',
            )
        except StockInsuficiente as error:
            form.add_error('cantidad', str(error))
        else:
            producto.refresh_from_db()
            motivo = dict(form.fields['motivo'].choices).get(datos['motivo'], '')
            messages.success(request, f"Se quitaron {movimiento.cantidad} unidades de «{producto.nombre}» "
                                      f"({motivo.lower()}). Stock actual: {producto.stock_actual}.")
            for aviso in avisos_stock_bajo([movimiento]):
                messages.warning(request, aviso)
            return redirect(_volver_a_lista(request))

    return render(request, 'inventario/salida_form.html', {
        'producto': producto, 'form': form, 'volver': _volver_a_lista(request),
    })


@login_required
@rol_requerido(*ROLES_INVENTARIO)
def retirar(request, pk):
    """Quitar un producto del inventario (no se borra: su historial queda en el Kardex)."""
    producto = get_object_or_404(Producto, pk=pk, activo=True)
    form = RetirarProductoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        baja = retirar_producto(producto.pk, usuario=request.user, motivo=form.cleaned_data['motivo'],
                                nota=form.cleaned_data.get('observacion') or '')
        texto = f"«{producto.nombre}» se retiró del inventario."
        if baja:
            texto += f" Se dieron de baja sus {baja.cantidad} unidades restantes."
        messages.success(request, texto + " Puedes reactivarlo desde la pestaña «Retirados».")
        return redirect(_volver_a_lista(request))

    return render(request, 'inventario/producto_retirar.html', {
        'producto': producto, 'form': form,
        'en_servicios': producto.usos_en_servicios.count(),
        'volver': _volver_a_lista(request),
    })


@login_required
@rol_requerido(*ROLES_INVENTARIO)
@require_POST
def reactivar(request, pk):
    producto = get_object_or_404(Producto, pk=pk, activo=False)
    producto.activo = True
    producto.save(update_fields=['activo', 'fecha_actualizacion'])
    messages.success(request, f"«{producto.nombre}» volvió al inventario con stock {producto.stock_actual}. "
                              "Usa «Añadir» para reponerlo.")
    return redirect(f"{reverse('inventario:lista')}?retirados=1")


@login_required
@rol_requerido(*ROLES_INVENTARIO)
def cargar_catalogo_excel(request):
    """PB-13 / RF09: carga masiva del catálogo desde la plantilla de Excel."""
    errores, avisos, exitos = [], [], 0

    if request.method == 'POST':
        form = CargaExcelForm(request.POST, request.FILES)
        if form.is_valid():
            exitos, errores, avisos = procesar_catalogo(request.FILES['archivo_excel'], request.user)
            if exitos:
                messages.success(request, f"Se cargaron {exitos} registros en el catálogo.")
            if errores:
                messages.warning(request, f"{len(errores)} fila(s) no se cargaron. Corrígelas y vuelve a subir solo esas filas.")
            if not exitos and not errores:
                messages.warning(request, "El archivo no tenía filas con datos.")
    else:
        form = CargaExcelForm()

    return render(request, 'inventario/cargar_excel.html', {
        'form': form, 'errores': errores, 'avisos': avisos, 'exitos': exitos,
    })


@login_required
@rol_requerido(*ROLES_INVENTARIO)
def exportar_inventario_excel(request):
    """
    Genera un archivo .xlsx con el listado actual de productos en inventario.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario Prados Pets"

    headers = [
        'Código', 'Código Barras', 'Nombre', 'Categoría', 'Proveedor',
        'Precio Compra ($)', 'Precio Venta ($)', 'Stock Actual', 'Stock Mínimo', 'Vence', 'Estado'
    ]
    ws.append(headers)

    header_fill = PatternFill(start_color="1E1530", end_color="1E1530", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    productos = Producto.objects.filter(activo=True).select_related('categoria', 'proveedor')
    for prod in productos:
        estado = "VENCIDO" if prod.vencido and prod.stock_actual else ("REABASTECER" if prod.necesita_reposicion else "OK")
        cat_nombre = prod.categoria.nombre if prod.categoria else "General"
        prov_nombre = prod.proveedor.nombre if prod.proveedor else "N/A"
        
        ws.append([
            prod.codigo,
            prod.codigo_barras or '',
            prod.nombre,
            cat_nombre,
            prov_nombre,
            float(prod.precio_compra),
            float(prod.precio_venta),
            prod.stock_actual,
            prod.stock_minimo,
            prod.fecha_vencimiento.strftime('%d/%m/%Y') if prod.fecha_vencimiento else '',
            estado
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Inventario_Prados_Pets.xlsx"'
    wb.save(response)
    return response


@login_required
@rol_requerido(*ROLES_INVENTARIO)
def descargar_plantilla_excel(request):
    """
    Entrega la plantilla oficial (static/plantillas/Plantilla_Carga_Inventario_PradosPets.xlsx,
    con hoja de instrucciones, listas desplegables y 41 ejemplos). Si no está, genera una básica.
    """
    ruta = finders.find('plantillas/Plantilla_Carga_Inventario_PradosPets.xlsx')
    if ruta:
        with open(ruta, 'rb') as fh:
            response = HttpResponse(
                fh.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
        response['Content-Disposition'] = 'attachment; filename="Plantilla_Carga_Inventario_PradosPets.xlsx"'
        return response

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plantilla Catálogo"

    headers = [
        'Tipo', 'Codigo', 'Nombre', 'Descripcion', 'Precio', 'StockMinimo',
        'PrincipioActivo', 'Concentracion', 'Presentacion', 'RequiereReceta',
        'NumeroLote', 'FechaVencimiento', 'CantidadLote'
    ]
    ws.append(headers)

    ejemplos = [
        ['MEDICAMENTO', 'MED-001', 'Amoxicilina 500mg', 'Antibiótico de amplio espectro', 25000, 5, 'Amoxicilina', '500 mg', 'Frasco 100ml', 'SI', 'LOTE-2026-A', '2027-12-31', 30],
        ['PRODUCTO', 'PROD-001', 'Champú Antipulgas 250ml', 'Higiene y cuidado canino', 32000, 3, '', '', 'Frasco 250ml', 'NO', 'LOTE-2026-B', '2028-06-30', 15],
        ['SERVICIO', 'SERV-001', 'Consulta Médica General', 'Atención médica veterinaria integral', 45000, 0, '', '', '', 'NO', '', '', '']
    ]
    for row in ejemplos:
        ws.append(row)

    header_fill = PatternFill(start_color="1E1530", end_color="1E1530", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Plantilla_Carga_Catalogo_PradosPets.xlsx"'
    wb.save(response)
    return response


@solo_inventario
class KardexListView(LoginRequiredMixin, ListView):
    model = MovimientoInventario
    template_name = 'inventario/kardex.html'
    context_object_name = 'movimientos'
    paginate_by = 20


# ---------------------------------------------------------------------------
# PB-17 / RF10 · Descuento automático del stock
# ---------------------------------------------------------------------------

def _producto_a_dict(producto):
    disponible, vencidas = disponibilidad(producto)
    return {
        'id': producto.pk,
        'codigo': producto.codigo,
        'nombre': producto.nombre,
        'es_medicamento': hasattr(producto, 'medicamento'),
        'disponible': disponible,
        'vencidas': vencidas,
        'stock_minimo': producto.stock_minimo,
        'proximo_vence': producto.fecha_vencimiento.strftime('%d/%m/%Y') if producto.fecha_vencimiento else '',
    }


@login_required
@rol_requerido(*ROLES_INVENTARIO)
def buscar_producto(request):
    """AJAX: productos activos por nombre o código, con las unidades que se pueden usar."""
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    productos = (Producto.objects.filter(activo=True)
                 .filter(models.Q(nombre__icontains=q) | models.Q(codigo__icontains=q))
                 .select_related('medicamento').order_by('nombre')[:12])
    return JsonResponse([_producto_a_dict(p) for p in productos], safe=False)


@login_required
@rol_requerido(*ROLES_INVENTARIO)
def insumos_peluqueria(request):
    """Qué insumos gasta cada servicio de peluquería (se descuentan al agendar la cita)."""
    if request.method == 'POST':
        if 'eliminar' in request.POST:
            InsumoServicio.objects.filter(pk=request.POST.get('eliminar')).delete()
            messages.success(request, 'Insumo quitado del servicio.')
            return redirect('inventario:insumos_peluqueria')

        servicio = request.POST.get('servicio', '')
        tamano = request.POST.get('tamano', '')
        producto_id = (request.POST.get('producto') or '').strip()
        cantidad = (request.POST.get('cantidad') or '').strip()
        producto = Producto.objects.filter(pk=producto_id, activo=True).first() if producto_id.isdigit() else None

        errores = []
        if servicio not in dict(InsumoServicio.SERVICIOS):
            errores.append('Elige el servicio de peluquería.')
        if tamano not in dict(InsumoServicio.TAMANOS):
            errores.append('El tamaño elegido no es válido.')
        if producto is None:
            errores.append('Elige un producto activo del inventario.')
        if not cantidad.isdigit() or not (1 <= int(cantidad) <= 99):
            errores.append('La cantidad por servicio debe ser un número entero entre 1 y 99.')
        if errores:
            for e in errores:
                messages.error(request, e)
            return redirect('inventario:insumos_peluqueria')

        insumo, creado = InsumoServicio.objects.update_or_create(
            servicio=servicio, tamano=tamano, producto=producto,
            defaults={'cantidad': int(cantidad)},
        )
        messages.success(request, ('Insumo agregado: ' if creado else 'Cantidad actualizada: ') + str(insumo) + '.')
        return redirect('inventario:insumos_peluqueria')

    grupos = []
    insumos = InsumoServicio.objects.select_related('producto').order_by('producto__nombre')
    for clave, nombre in InsumoServicio.SERVICIOS:
        filas = [i for i in insumos if i.servicio == clave]
        for i in filas:
            i.disponible = disponibilidad(i.producto)[0]
        grupos.append({'clave': clave, 'nombre': nombre, 'insumos': filas})

    return render(request, 'inventario/insumos_peluqueria.html', {
        'grupos': grupos,
        'servicios': InsumoServicio.SERVICIOS,
        'tamanos': InsumoServicio.TAMANOS,
        'productos': Producto.objects.filter(activo=True).order_by('nombre'),
    })