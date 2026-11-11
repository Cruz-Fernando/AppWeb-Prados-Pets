"""
Carga masiva del catálogo desde la plantilla de Excel (PB-13 / RF09).

Reglas (las mismas que explica la hoja «Instrucciones» de la plantilla):
  - Se lee SOLO la primera hoja, aunque el archivo se haya guardado mirando otra.
  - La fila 1 debe tener los encabezados en el orden de la plantilla.
  - Cada fila se guarda o se rechaza completa (nunca a medias).
  - Las filas con error se informan con un mensaje en español y no se guardan;
    las demás sí.
"""

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import openpyxl
from django.db import transaction
from django.utils import timezone

from .models import Medicamento, MovimientoInventario, Producto, Servicio, StockLote

ENCABEZADOS = [
    "Tipo", "Codigo", "Nombre", "Descripcion", "Precio", "StockMinimo",
    "PrincipioActivo", "Concentracion", "Presentacion", "RequiereReceta",
    "NumeroLote", "FechaVencimiento", "CantidadLote",
]
TIPOS_VALIDOS = ("PRODUCTO", "MEDICAMENTO", "SERVICIO")
STOCK_MINIMO_DEFECTO = 5
MAX_LARGO_CODIGO = 50          # Servicio.codigo admite 50 caracteres
MAX_FILAS = 2000               # protege al servidor de archivos enormes


class ErrorFila(Exception):
    """Error de una fila, con un mensaje pensado para el usuario."""


# ---------------------------------------------------------------------------
# Utilidades de lectura
# ---------------------------------------------------------------------------

def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", texto.lower())


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)          # 1001.0 -> "1001"
    return str(valor).strip()


def _precio(valor):
    """Acepta 25000, 25000.5, '25000', '$25.000', '25.000 COP' o '1.800,50'."""
    if valor is None or _texto(valor) == "":
        raise ErrorFila("El precio es obligatorio.")
    if isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool):
        numero = Decimal(str(valor))
    else:
        limpio = re.sub(r"(?i)cop|\$|\s", "", str(valor))
        if "," in limpio and "." in limpio:          # 1.800,50
            limpio = limpio.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d{1,3}([.,]\d{3})+", limpio):   # 25.000 o 25,000
            limpio = re.sub(r"[.,]", "", limpio)
        else:
            limpio = limpio.replace(",", ".")
        try:
            numero = Decimal(limpio)
        except InvalidOperation:
            raise ErrorFila(f"Precio inválido ('{valor}'). Escribe solo el número, por ejemplo 25000.")
    if numero < 0:
        raise ErrorFila("El precio no puede ser negativo.")
    return numero.quantize(Decimal("0.01"))


def _entero(valor, campo, minimo=0):
    if isinstance(valor, bool):
        raise ErrorFila(f"{campo} debe ser un número entero.")
    try:
        numero = Decimal(str(valor).strip())
    except (InvalidOperation, ValueError):
        raise ErrorFila(f"{campo} debe ser un número entero (escribiste '{valor}').")
    if numero != numero.to_integral_value():
        raise ErrorFila(f"{campo} debe ser un número entero, sin decimales (escribiste '{valor}').")
    if numero < minimo:
        raise ErrorFila(f"{campo} debe ser mayor o igual a {minimo}.")
    return int(numero)


def _fecha(valor):
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ErrorFila(f"Fecha de vencimiento inválida ('{valor}'). Usa el formato AAAA-MM-DD, por ejemplo 2027-11-30.")


def _si_no(valor):
    texto = _normalizar(valor)
    if texto in ("", "no", "n", "false", "0"):
        return False
    if texto in ("si", "s", "true", "1"):
        return True
    raise ErrorFila(f"RequiereReceta debe ser SI o NO (escribiste '{valor}').")


# ---------------------------------------------------------------------------
# Proceso
# ---------------------------------------------------------------------------

def _validar_encabezados(fila):
    fila = list(fila or []) + [None] * len(ENCABEZADOS)
    for i, esperado in enumerate(ENCABEZADOS):
        if _normalizar(fila[i]) != _normalizar(esperado):
            letra = chr(ord("A") + i)
            return (f"La columna {letra} debería llamarse «{esperado}» y dice «{_texto(fila[i]) or 'vacío'}». "
                    "No cambies ni muevas los encabezados de la plantilla.")
    return None


def _guardar_fila(fila, usuario, hoy):
    (tipo, codigo, nombre, descripcion, precio, stock_min, principio, concentracion,
     presentacion, receta, num_lote, fecha_venc, cant_lote) = fila

    tipo = _normalizar(tipo).upper()
    codigo, nombre = _texto(codigo), _texto(nombre)
    if tipo not in TIPOS_VALIDOS:
        raise ErrorFila(f"Tipo inválido ('{_texto(fila[0])}'). Debe ser PRODUCTO, MEDICAMENTO o SERVICIO.")
    if not codigo:
        raise ErrorFila("El código es obligatorio.")
    if len(codigo) > MAX_LARGO_CODIGO:
        raise ErrorFila(f"El código tiene {len(codigo)} caracteres; el máximo es {MAX_LARGO_CODIGO}.")
    if not nombre:
        raise ErrorFila("El nombre es obligatorio.")
    precio = _precio(precio)
    descripcion = _texto(descripcion)

    if tipo == "SERVICIO":
        if Servicio.objects.filter(codigo__iexact=codigo).exists():
            raise ErrorFila(f"El código '{codigo}' ya existe como servicio; la fila no se duplica.")
        Servicio.objects.create(codigo=codigo, nombre=nombre, descripcion=descripcion, precio=precio)
        return []

    if Producto.objects.filter(codigo__iexact=codigo).exists():
        raise ErrorFila(f"El código '{codigo}' ya existe como producto o medicamento; la fila no se duplica.")

    stock_minimo = STOCK_MINIMO_DEFECTO if _texto(stock_min) == "" else _entero(stock_min, "StockMínimo")
    requiere_receta = _si_no(receta)

    # Lote inicial: si se llena algo del lote, deben venir el número y la cantidad
    num_lote = _texto(num_lote)
    hay_cantidad = _texto(cant_lote) != ""
    fecha_vencimiento = _fecha(fecha_venc)
    if (num_lote or hay_cantidad or fecha_vencimiento) and not (num_lote and hay_cantidad):
        falta = "NumeroLote" if not num_lote else "CantidadLote"
        raise ErrorFila(f"Para cargar el lote inicial llena NumeroLote y CantidadLote (falta {falta}).")
    cantidad = _entero(cant_lote, "CantidadLote", minimo=1) if hay_cantidad else 0
    if fecha_vencimiento and fecha_vencimiento <= hoy:
        raise ErrorFila(f"El lote {num_lote} venció el {fecha_vencimiento:%d/%m/%Y}; no se carga como stock disponible.")

    producto = Producto.objects.create(
        codigo=codigo,
        nombre=nombre,
        descripcion=descripcion,
        precio_venta=precio,
        stock_minimo=stock_minimo,
    )
    if tipo == "MEDICAMENTO":
        Medicamento.objects.create(
            producto=producto,
            principio_activo=_texto(principio),
            concentracion=_texto(concentracion),
            presentacion=_texto(presentacion),
            requiere_receta=requiere_receta,
        )

    avisos = []
    if num_lote:
        StockLote.objects.create(
            producto=producto,
            numero_lote=num_lote,
            fecha_vencimiento=fecha_vencimiento,
            cantidad=cantidad,
        )
        producto.stock_actual += cantidad
        producto.save(update_fields=["stock_actual", "fecha_actualizacion"])
        MovimientoInventario.objects.create(
            producto=producto,
            tipo="ENTRADA_COMPRA",
            cantidad=cantidad,
            precio_unitario_historico=precio,
            monto_total=precio * cantidad,
            usuario=usuario,
            observacion=f"Carga inicial Excel - Lote {num_lote}",
        )
        if fecha_vencimiento and (fecha_vencimiento - hoy).days <= 30:
            avisos.append(f"el lote {num_lote} vence en {(fecha_vencimiento - hoy).days} días")
    return avisos


def procesar_catalogo(archivo, usuario):
    """
    Devuelve (exitos, errores, avisos):
      - exitos: cuántas filas se guardaron
      - errores: [{'fila': n, 'error': texto}] filas rechazadas
      - avisos: [{'fila': n, 'aviso': texto}] filas guardadas que conviene revisar
    """
    try:
        wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
    except Exception:
        return 0, [{"fila": "-", "error": "No se pudo abrir el archivo. Debe ser un Excel .xlsx (usa la plantilla)."}], []

    hoja = wb.worksheets[0]          # la PRIMERA hoja, no la que estaba abierta al guardar
    filas = hoja.iter_rows(values_only=True)
    error_encabezados = _validar_encabezados(next(filas, None))
    if error_encabezados:
        wb.close()
        return 0, [{"fila": 1, "error": error_encabezados}], []

    hoy = timezone.localdate()
    exitos, errores, avisos = 0, [], []
    vistos = {}
    for numero, fila in enumerate(filas, start=2):
        fila = (list(fila) + [None] * len(ENCABEZADOS))[:len(ENCABEZADOS)]
        if not any(_texto(v) for v in fila):
            continue
        if numero > MAX_FILAS + 1:
            errores.append({"fila": numero, "error": f"Se procesan máximo {MAX_FILAS} filas por archivo; divide la carga."})
            break

        clave = (_normalizar(fila[0]) == "servicio", _texto(fila[1]).lower())
        if clave[1] and clave in vistos:
            errores.append({"fila": numero, "error": f"El código '{_texto(fila[1])}' está repetido en este archivo (ya aparece en la fila {vistos[clave]})."})
            continue

        try:
            with transaction.atomic():
                for aviso in _guardar_fila(fila, usuario, hoy):
                    avisos.append({"fila": numero, "aviso": aviso})
            exitos += 1
            vistos[clave] = numero
        except ErrorFila as e:
            errores.append({"fila": numero, "error": str(e)})
        except Exception:
            errores.append({"fila": numero, "error": "No se pudo guardar la fila por un error inesperado. Revisa los datos o avisa al administrador."})

    wb.close()
    return exitos, errores, avisos