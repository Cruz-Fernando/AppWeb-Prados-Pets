from datetime import datetime
import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect

from apps.usuarios.permissions import rol_requerido
from .forms import CargaExcelForm
from .models import Producto, Medicamento, Servicio, StockLote


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def cargar_catalogo_excel(request):
    """
    RF09 / PB-13 (SW-10): Carga masiva de catálogo desde archivo Excel (.xlsx).
    Procesa filas individualmente e informa errores específicos por número de fila.
    """
    errores = []
    exitos = 0

    if request.method == 'POST':
        form = CargaExcelForm(request.POST, request.FILES)
        if form.is_valid():
            archivo = request.FILES['archivo_excel']
            
            try:
                wb = openpyxl.load_workbook(archivo, data_only=True)
                sheet = wb.active
            except Exception as e:
                messages.error(request, f"Error al abrir el archivo Excel: {str(e)}")
                return render(request, 'inventario/cargar_excel.html', {'form': form})

            # Encabezado esperado en la fila 1:
            # 1:Tipo | 2:Codigo | 3:Nombre | 4:Descripcion | 5:Precio | 6:StockMinimo | 7:PrincipioActivo | 8:Concentracion | 9:Presentacion | 10:RequiereReceta | 11:NumeroLote | 12:FechaVencimiento | 13:CantidadLote

            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                if not any(row):  # Ignorar filas vacías
                    continue

                tipo = str(row[0] or '').strip().upper()
                codigo = str(row[1] or '').strip()
                nombre = str(row[2] or '').strip()
                descripcion = str(row[3] or '').strip()
                precio_raw = row[4]
                stock_min_raw = row[5]

                # Validaciones mínimas
                if not tipo or tipo not in ('PRODUCTO', 'MEDICAMENTO', 'SERVICIO'):
                    errores.append({'fila': row_idx, 'error': f"Tipo de ítem inválido ('{tipo}'). Debe ser PRODUCTO, MEDICAMENTO o SERVICIO."})
                    continue

                if not codigo:
                    errores.append({'fila': row_idx, 'error': "El campo 'Código' es obligatorio."})
                    continue

                if not nombre:
                    errores.append({'fila': row_idx, 'error': "El campo 'Nombre' es obligatorio."})
                    continue

                try:
                    precio = float(precio_raw)
                    if precio < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    errores.append({'fila': row_idx, 'error': f"Precio inválido ('{precio_raw}'). Debe ser un número mayor o igual a 0."})
                    continue

                # Procesamiento por tipo de entidad
                try:
                    with transaction.atomic():
                        if tipo == 'SERVICIO':
                            if Servicio.objects.filter(codigo=codigo).exists():
                                errores.append({'fila': row_idx, 'error': f"El servicio con código '{codigo}' ya existe."})
                                continue

                            Servicio.objects.create(
                                codigo=codigo,
                                nombre=nombre,
                                descripcion=descripcion,
                                precio=precio,
                            )
                            exitos += 1

                        elif tipo in ('PRODUCTO', 'MEDICAMENTO'):
                            if Producto.objects.filter(codigo=codigo).exists():
                                errores.append({'fila': row_idx, 'error': f"El producto/medicamento con código '{codigo}' ya existe."})
                                continue

                            try:
                                stock_min = int(stock_min_raw) if stock_min_raw is not None else 5
                            except ValueError:
                                stock_min = 5

                            producto = Producto.objects.create(
                                codigo=codigo,
                                nombre=nombre,
                                descripcion=descripcion,
                                precio_venta=precio,
                                stock_minimo=stock_min,
                            )

                            if tipo == 'MEDICAMENTO':
                                principio = str(row[6] or '').strip()
                                concentracion = str(row[7] or '').strip()
                                presentacion = str(row[8] or '').strip()
                                receta_val = str(row[9] or '').strip().upper() in ('SI', 'S', 'TRUE', '1')

                                Medicamento.objects.create(
                                    producto=producto,
                                    principio_activo=principio,
                                    concentracion=concentracion,
                                    presentacion=presentacion,
                                    requiere_receta=receta_val,
                                )

                            # Opcional: Procesar Stock / Lote si viene en la fila
                            num_lote = str(row[10] or '').strip()
                            fecha_venc_raw = row[11]
                            cant_lote_raw = row[12]

                            if num_lote and cant_lote_raw is not None:
                                try:
                                    cant_lote = int(cant_lote_raw)
                                    fecha_venc = None
                                    if isinstance(fecha_venc_raw, datetime):
                                        fecha_venc = fecha_venc_raw.date()
                                    elif isinstance(fecha_venc_raw, str) and fecha_venc_raw.strip():
                                        fecha_venc = datetime.strptime(fecha_venc_raw.strip(), "%Y-%m-%d").date()

                                    StockLote.objects.create(
                                        producto=producto,
                                        numero_lote=num_lote,
                                        fecha_vencimiento=fecha_venc,
                                        cantidad=cant_lote,
                                    )
                                except Exception as err_lote:
                                    errores.append({'fila': row_idx, 'error': f"Error al registrar lote: {str(err_lote)}"})
                                    # La transacción reitera/cancela el producto creado
                                    raise err_lote

                            exitos += 1

                except Exception as ex:
                    if not any(e['fila'] == row_idx for e in errores):
                        errores.append({'fila': row_idx, 'error': f"Error al guardar registro: {str(ex)}"})

            if exitos > 0:
                messages.success(request, f"Se cargaron exitosamente {exitos} registros en el catálogo.")
            if not errores and exitos == 0:
                messages.warning(request, "El archivo no contenía datos válidos para procesar.")

    else:
        form = CargaExcelForm()

    return render(
        request,
        'inventario/cargar_excel.html',
        {'form': form, 'errores': errores, 'exitos': exitos}
    )