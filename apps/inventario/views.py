from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, models
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView

from apps.usuarios.permissions import rol_requerido
from .carga_excel import procesar_catalogo
from .forms import ProductoForm, ReposicionForm, CargaExcelForm
from .models import Producto, Medicamento, Servicio, StockLote, MovimientoInventario, CategoriaProducto


class InventarioListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'inventario/inventario_list.html'
    context_object_name = 'productos'
    paginate_by = 15

    def get_queryset(self):
        queryset = Producto.objects.filter(activo=True).select_related('categoria', 'proveedor')
        q = self.request.GET.get('q')
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
        return context


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


@login_required
def registrar_reposicion(request):
    if request.method == 'POST':
        form = ReposicionForm(request.POST)
        if form.is_valid():
            producto = form.cleaned_data['producto']
            cantidad = form.cleaned_data['cantidad']
            nuevo_costo = form.cleaned_data.get('nuevo_precio_compra')
            observacion = form.cleaned_data.get('observacion')

            with transaction.atomic():
                if nuevo_costo is not None:
                    producto.precio_compra = nuevo_costo
                
                producto.stock_actual += cantidad
                producto.save()

                costo_aplicado = nuevo_costo if nuevo_costo is not None else producto.precio_compra

                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo='ENTRADA_COMPRA',
                    cantidad=cantidad,
                    precio_unitario_historico=costo_aplicado,
                    monto_total=cantidad * costo_aplicado,
                    usuario=request.user,
                    observacion=observacion or "Reabastecimiento de stock"
                )

            messages.success(request, f"Stock actualizado para {producto.nombre}. Nuevo stock: {producto.stock_actual}")
            return redirect('inventario:lista')
    else:
        form = ReposicionForm()
    
    return render(request, 'inventario/reposicion_form.html', {'form': form})


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
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
def exportar_inventario_excel(request):
    """
    Genera un archivo .xlsx con el listado actual de productos en inventario.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario Prados Pets"

    headers = [
        'Código', 'Código Barras', 'Nombre', 'Categoría', 'Proveedor',
        'Precio Compra ($)', 'Precio Venta ($)', 'Stock Actual', 'Stock Mínimo', 'Estado'
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
        estado = "REABASTECER" if prod.necesita_reposicion else "OK"
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


class KardexListView(LoginRequiredMixin, ListView):
    model = MovimientoInventario
    template_name = 'inventario/kardex.html'
    context_object_name = 'movimientos'
    paginate_by = 20