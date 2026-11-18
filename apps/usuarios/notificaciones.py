"""
Centro de notificaciones (campana de la barra superior).

Reúne en un solo lugar lo que el personal debe atender, según su rol:
  - Recordatorios de vacunación y baño por avisar (de hoy o atrasados).
  - Alertas de inventario: agotados, en stock mínimo, vencidos y por vencer.

La campana pide este contenido después de cargar la página (fetch), así que
no retrasa ninguna pantalla.
"""

from datetime import timedelta

from django.db.models import Count, F, Q
from django.urls import reverse
from django.utils import timezone

from .permissions import tiene_rol

ROLES_RECORDATORIOS = ("administrador", "veterinario", "auxiliar", "groomer")
ROLES_INVENTARIO = ("administrador", "veterinario", "auxiliar")

# Cuántos recordatorios se muestran en la campana (el resto, en la pantalla).
MAX_RECORDATORIOS = 5
DIAS_POR_VENCER = 30


def _alertas_inventario(hoy):
    # Import local: inventario importa de usuarios al arrancar.
    from apps.inventario.models import Producto

    activo = Q(activo=True)
    con_unidades = Q(stock_actual__gt=0)
    resumen = Producto.objects.aggregate(
        agotados=Count("pk", filter=activo & Q(stock_actual=0)),
        bajo=Count("pk", filter=activo & con_unidades & Q(stock_actual__lte=F("stock_minimo"))),
        vencidos=Count("pk", filter=activo & con_unidades & Q(fecha_vencimiento__lt=hoy)),
        por_vencer=Count("pk", filter=activo & con_unidades & Q(
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=hoy + timedelta(days=DIAS_POR_VENCER),
        )),
    )
    url = reverse("inventario:lista")
    filas = [
        ("vencidos", "peligro", "producto vencido con unidades", "productos vencidos con unidades",
         "Quítalos con «Quitar» y el motivo «Vencimiento»."),
        ("agotados", "peligro", "producto agotado", "productos agotados", "Sin unidades: repónlos con «Añadir»."),
        ("bajo", "aviso", "producto en stock mínimo", "productos en stock mínimo", "Conviene reabastecer pronto."),
        ("por_vencer", "info", f"producto vence en {DIAS_POR_VENCER} días", f"productos vencen en {DIAS_POR_VENCER} días",
         "Úsalos primero."),
    ]
    alertas = []
    for clave, nivel, singular, plural, ayuda in filas:
        n = resumen[clave]
        if n:
            alertas.append({
                "clave": clave,
                "nivel": nivel,
                "total": n,
                "texto": f"{n} {singular if n == 1 else plural}",
                "ayuda": ayuda,
                "url": f"{url}?estado={clave}",
            })
    return alertas


def obtener_notificaciones(usuario, hoy=None):
    """Devuelve lo que la campana muestra a este usuario."""
    hoy = hoy or timezone.localdate()
    datos = {
        "recordatorios": [],
        "total_recordatorios": 0,
        "inventario": [],
        "ve_recordatorios": tiene_rol(usuario, *ROLES_RECORDATORIOS),
        "ve_inventario": tiene_rol(usuario, *ROLES_INVENTARIO),
    }

    if datos["ve_recordatorios"]:
        from apps.clinico.recordatorios import calcular_recordatorios

        pendientes = calcular_recordatorios(hoy)["pendientes"]
        datos["recordatorios"] = pendientes[:MAX_RECORDATORIOS]
        datos["total_recordatorios"] = len(pendientes)

    if datos["ve_inventario"]:
        datos["inventario"] = _alertas_inventario(hoy)

    # Lo que cuenta la burbuja roja: cada recordatorio por avisar y cada tipo
    # de alerta de inventario urgente (no se suma producto por producto).
    datos["total"] = datos["total_recordatorios"] + sum(
        1 for a in datos["inventario"] if a["nivel"] != "info"
    )
    return datos
