"""
Medicamentos e insumos usados en una atención clínica (PB-17 / RF10).

El formulario del registro clínico envía filas con dos listas paralelas:
    insumo_producto = [id, id, ...]
    insumo_cantidad = [n,  n,  ...]
Aquí se leen, se validan y, al guardar el registro, se descuentan del
inventario en la misma transacción: si un producto no alcanza, no se guarda
ni el registro ni ningún descuento.
"""

from apps.inventario.models import Producto
from apps.inventario.services import disponibilidad, descontar_stock

MAX_FILAS = 30
MAX_CANTIDAD = 999


def leer_insumos(post):
    """
    Devuelve (insumos, filas, errores).
      - insumos: [(producto, cantidad)] sin repetidos (si un producto viene dos veces se suman)
      - filas:   lo que escribió el usuario, para volver a pintarlo si hay errores
      - errores: textos para mostrar
    """
    ids = post.getlist('insumo_producto')
    cantidades = post.getlist('insumo_cantidad')
    errores, filas, pedidos = [], [], {}

    for i, crudo in enumerate(ids[:MAX_FILAS]):
        crudo = (crudo or '').strip()
        texto_cantidad = (cantidades[i] if i < len(cantidades) else '').strip()
        if not crudo:
            continue
        if not crudo.isdigit():
            errores.append('Uno de los productos no es válido. Vuelve a buscarlo en la lista.')
            continue
        producto = Producto.objects.filter(pk=int(crudo), activo=True).first()
        if producto is None:
            errores.append('Uno de los productos ya no existe o está inactivo en el inventario.')
            continue
        filas.append({'id': producto.pk, 'codigo': producto.codigo, 'nombre': producto.nombre,
                      'cantidad': texto_cantidad, 'disponible': disponibilidad(producto)[0]})
        if not texto_cantidad.isdigit() or not (1 <= int(texto_cantidad) <= MAX_CANTIDAD):
            errores.append(f"La cantidad de «{producto.nombre}» debe ser un número entero entre 1 y {MAX_CANTIDAD}.")
            continue
        pedidos[producto.pk] = (producto, pedidos.get(producto.pk, (producto, 0))[1] + int(texto_cantidad))

    if len(ids) > MAX_FILAS:
        errores.append(f"Se pueden registrar máximo {MAX_FILAS} productos por atención.")

    # Aviso temprano (la comprobación definitiva se hace al descontar, con bloqueo)
    for producto, cantidad in pedidos.values():
        disponible, vencidas = disponibilidad(producto)
        if cantidad > disponible:
            mensaje = (f"No hay stock suficiente de «{producto.nombre}»: pediste {cantidad} "
                       f"y hay {disponible} disponible{'s' if disponible != 1 else ''}.")
            if vencidas:
                mensaje += f" ({vencidas} vencida{'s' if vencidas != 1 else ''} no se pueden usar.)"
            errores.append(mensaje)

    return list(pedidos.values()), filas, errores


def descontar_insumos(registro, insumos, usuario):
    """Descuenta del inventario los insumos de un registro ya guardado. Lanza StockInsuficiente."""
    movimientos = []
    for producto, cantidad in insumos:
        movimientos.append(descontar_stock(
            producto.pk, cantidad,
            tipo='SALIDA_CLINICA',
            usuario=usuario,
            observacion=f"{registro.numero} · {registro.get_tipo_display()} · {registro.mascota.nombre}",
            registro_clinico=registro,
        ))
    return movimientos