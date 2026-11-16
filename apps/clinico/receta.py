"""
Récipe médico de un registro clínico (PB-15 / RF07).

El formulario del registro envía filas con listas paralelas:
    receta_producto, receta_dosis, receta_frecuencia, receta_duracion, receta_indicaciones
Aquí se leen y validan (solo medicamentos activos del catálogo) y se guardan
como RecetaItem dentro de la misma transacción que el registro.
"""

from apps.inventario.models import Producto

from .models import RecetaItem

MAX_ITEMS = 20
LIMITES = {'dosis': 100, 'frecuencia': 100, 'duracion': 100, 'indicaciones': 500}
ETIQUETAS = {'dosis': 'la dosis', 'frecuencia': 'la frecuencia', 'duracion': 'la duración'}


def _detalle_medicamento(producto):
    med = getattr(producto, 'medicamento', None)
    if med is None:
        return '', '', ''
    return med.principio_activo or '', med.concentracion or '', med.presentacion or ''


def _fila(producto, dosis='', frecuencia='', duracion='', indicaciones=''):
    activo, concentracion, presentacion = _detalle_medicamento(producto)
    return {
        'id': producto.pk, 'codigo': producto.codigo, 'nombre': producto.nombre,
        'principio_activo': activo, 'concentracion': concentracion, 'presentacion': presentacion,
        'dosis': dosis, 'frecuencia': frecuencia, 'duracion': duracion, 'indicaciones': indicaciones,
    }


def leer_receta(post):
    """
    Devuelve (items, filas, errores).
      - items:   [{'producto', 'dosis', 'frecuencia', 'duracion', 'indicaciones'}] ya validados
      - filas:   lo que escribió el usuario, para volver a pintarlo si hay errores
      - errores: textos para mostrar
    """
    ids = post.getlist('receta_producto')
    columnas = {c: post.getlist(f'receta_{c}') for c in LIMITES}
    items, filas, errores = [], [], []

    def valor(columna, i):
        lista = columnas[columna]
        return (lista[i] if i < len(lista) else '').strip()

    for i, crudo in enumerate(ids[:MAX_ITEMS]):
        crudo = (crudo or '').strip()
        if not crudo:
            continue
        if not crudo.isdigit():
            errores.append('Uno de los medicamentos del récipe no es válido. Vuelve a buscarlo en la lista.')
            continue
        producto = (Producto.objects.filter(pk=int(crudo), activo=True, medicamento__isnull=False)
                    .select_related('medicamento').first())
        if producto is None:
            errores.append('Uno de los medicamentos del récipe ya no está activo en el catálogo.')
            continue

        datos = {c: valor(c, i) for c in LIMITES}
        filas.append(_fila(producto, **datos))

        faltan = [ETIQUETAS[c] for c in ETIQUETAS if not datos[c]]
        if faltan:
            errores.append(f"«{producto.nombre}»: falta {' y '.join(faltan)}.")
            continue
        largos = [c for c, maximo in LIMITES.items() if len(datos[c]) > maximo]
        if largos:
            errores.append(f"«{producto.nombre}»: el texto de {largos[0]} es demasiado largo "
                           f"(máximo {LIMITES[largos[0]]} caracteres).")
            continue
        items.append({'producto': producto, **datos})

    if len(ids) > MAX_ITEMS:
        errores.append(f"Un récipe puede tener máximo {MAX_ITEMS} medicamentos.")
    return items, filas, errores


def firma(items):
    """Forma comparable de una receta (para saber si cambió al editar)."""
    return [(i['producto'].pk, i['dosis'], i['frecuencia'], i['duracion'], i['indicaciones'])
            for i in items]


def _firma_guardada(registro):
    return [(i.producto_id, i.dosis, i.frecuencia, i.duracion, i.indicaciones)
            for i in registro.receta_items.all()]


def guardar_receta(registro, items):
    """Crea las líneas del récipe de un registro recién guardado."""
    RecetaItem.objects.bulk_create([
        RecetaItem(registro=registro, producto=i['producto'], dosis=i['dosis'],
                   frecuencia=i['frecuencia'], duracion=i['duracion'],
                   indicaciones=i['indicaciones'], orden=n)
        for n, i in enumerate(items)
    ])


def reemplazar_receta(registro, items):
    """Sustituye el récipe de un registro. Devuelve True si hubo cambios."""
    if _firma_guardada(registro) == firma(items):
        return False
    registro.receta_items.all().delete()
    guardar_receta(registro, items)
    return True


def texto_items(items):
    """Resumen en una línea de una receta ya validada (bitácora de cambios)."""
    return '; '.join(f"{i['producto'].nombre} – {i['dosis']} – {i['frecuencia']} – {i['duracion']}"
                     for i in items)


def texto_guardado(registro):
    """Resumen en una línea del récipe guardado de un registro."""
    return '; '.join(str(i).replace(' · ', ' – ') for i in registro.receta_items.select_related('producto'))


def filas_de_registro(registro):
    """Filas para pintar el récipe guardado en el formulario de edición."""
    return [_fila(i.producto, i.dosis, i.frecuencia, i.duracion, i.indicaciones)
            for i in registro.receta_items.select_related('producto__medicamento')]