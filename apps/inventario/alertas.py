"""
Alertas de inventario (PB-21 / RF11): stock bajo y vencimiento.

Una sola definición para la campana de notificaciones y para los filtros de
la lista del inventario (?estado=...), así las dos siempre cuentan lo mismo.

Umbrales del acta (no dependen del stock mínimo de cada producto):
  - agotado: 0 unidades                      → rojo
  - crítico: menos de 2 unidades (1)         → rojo
  - bajo:    menos de 5 unidades (2 a 4)     → amarillo

Vencimiento: por el lote del producto (número de lote + fecha). Un producto
sin unidades no alerta por vencimiento: no hay nada que retirar.
"""

from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .models import UMBRAL_STOCK_BAJO, UMBRAL_STOCK_CRITICO, Producto

DIAS_POR_VENCER = 30
# Cuántos productos se detallan por alerta en la campana (el resto, en la lista).
MAX_DETALLE = 3


@dataclass(frozen=True)
class TipoAlerta:
    clave: str
    nivel: str            # peligro (rojo) · aviso (amarillo) · info (azul, no suma en la burbuja)
    filtro: str           # texto del filtro en la lista del inventario
    singular: str
    plural: str
    ayuda: str
    por_fecha: bool = False   # se ordena y detalla por fecha de vencimiento


TIPOS = (
    TipoAlerta("vencidos", "peligro", "Vencidos con unidades",
               "producto vencido con unidades", "productos vencidos con unidades",
               "Quítalos con «Quitar» y el motivo «Vencimiento».", por_fecha=True),
    TipoAlerta("agotados", "peligro", "Agotados",
               "producto agotado", "productos agotados",
               "Sin unidades: repónlos con «Añadir»."),
    TipoAlerta("critico", "peligro", f"Stock crítico (menos de {UMBRAL_STOCK_CRITICO})",
               f"producto en stock crítico (menos de {UMBRAL_STOCK_CRITICO})",
               f"productos en stock crítico (menos de {UMBRAL_STOCK_CRITICO})",
               "Queda 1 unidad: repón cuanto antes."),
    TipoAlerta("bajo", "aviso", f"Stock bajo (menos de {UMBRAL_STOCK_BAJO})",
               f"producto en stock bajo (menos de {UMBRAL_STOCK_BAJO})",
               f"productos en stock bajo (menos de {UMBRAL_STOCK_BAJO})",
               "Conviene reabastecer pronto."),
    TipoAlerta("por_vencer", "info", f"Vencen en {DIAS_POR_VENCER} días",
               f"producto vence en {DIAS_POR_VENCER} días", f"productos vencen en {DIAS_POR_VENCER} días",
               "Úsalos primero.", por_fecha=True),
)


def condiciones(hoy=None):
    """{clave: Q} de cada alerta, sobre productos activos."""
    hoy = hoy or timezone.localdate()
    con_unidades = Q(stock_actual__gt=0)
    return {
        "vencidos": con_unidades & Q(fecha_vencimiento__lt=hoy),
        "agotados": Q(stock_actual=0),
        "critico": con_unidades & Q(stock_actual__lt=UMBRAL_STOCK_CRITICO),
        "bajo": Q(stock_actual__gte=UMBRAL_STOCK_CRITICO, stock_actual__lt=UMBRAL_STOCK_BAJO),
        "por_vencer": con_unidades & Q(fecha_vencimiento__gte=hoy,
                                       fecha_vencimiento__lte=hoy + timedelta(days=DIAS_POR_VENCER)),
    }


def _cumple(clave, p, hoy):
    """La misma regla de condiciones(), en Python (para clasificar con una sola consulta)."""
    if clave == "agotados":
        return p.stock_actual == 0
    if clave == "critico":
        return 0 < p.stock_actual < UMBRAL_STOCK_CRITICO
    if clave == "bajo":
        return UMBRAL_STOCK_CRITICO <= p.stock_actual < UMBRAL_STOCK_BAJO
    if not p.stock_actual or not p.fecha_vencimiento:
        return False
    if clave == "vencidos":
        return p.fecha_vencimiento < hoy
    return hoy <= p.fecha_vencimiento <= hoy + timedelta(days=DIAS_POR_VENCER)   # por_vencer


def alertas_inventario(hoy=None, max_detalle=MAX_DETALLE):
    """
    Alertas que se cumplen hoy, en orden de urgencia, cada una con los primeros
    productos (nombre, lote, fecha y cantidad) para verlos sin salir de la
    campana. Una sola consulta.
    """
    hoy = hoy or timezone.localdate()
    cond = condiciones(hoy)
    cualquiera = Q()
    for q in cond.values():
        cualquiera |= q
    candidatos = list(
        Producto.objects.filter(activo=True).filter(cualquiera)
        .only("pk", "codigo", "nombre", "stock_actual", "fecha_vencimiento", "numero_lote")
        .order_by("stock_actual", "nombre", "pk")
    )

    lista = reverse("inventario:lista")
    alertas = []
    for tipo in TIPOS:
        productos = [p for p in candidatos if _cumple(tipo.clave, p, hoy)]
        if not productos:
            continue
        if tipo.por_fecha:
            productos.sort(key=lambda p: (p.fecha_vencimiento, p.nombre, p.pk))
        total = len(productos)
        url = f"{lista}?estado={tipo.clave}"
        alertas.append({
            "clave": tipo.clave,
            "nivel": tipo.nivel,
            "total": total,
            "texto": f"{total} {tipo.singular if total == 1 else tipo.plural}",
            "ayuda": tipo.ayuda,
            "url": url,
            "por_fecha": tipo.por_fecha,
            # Cada producto abre la lista filtrada por esa alerta y por su código
            "productos": [{"producto": p, "url": f"{url}&{urlencode({'q': p.codigo})}"}
                          for p in productos[:max_detalle]],
            "faltan": max(total - max_detalle, 0),
        })
    return alertas


def aviso_tras_salida(producto):
    """Texto para avisar en pantalla que el producto quedó agotado, crítico o bajo ('' si no)."""
    n = producto.stock_actual
    nivel = producto.nivel_stock
    if nivel == "agotado":
        return f"«{producto.nombre}» quedó agotado. Repónlo con «Añadir»."
    if nivel == "critico":
        return (f"«{producto.nombre}» quedó con {n} unidad: stock crítico "
                f"(menos de {UMBRAL_STOCK_CRITICO}). Repónlo cuanto antes.")
    if nivel == "bajo":
        return (f"«{producto.nombre}» quedó con {n} unidades: stock bajo "
                f"(menos de {UMBRAL_STOCK_BAJO}). Conviene reponerlo.")
    return ""
