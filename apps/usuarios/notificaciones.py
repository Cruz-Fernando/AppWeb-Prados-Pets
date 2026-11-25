"""
Centro de notificaciones (campana de la barra superior).

Reúne en un solo lugar lo que el personal debe atender, según su rol:
  - Recordatorios de vacunación y baño por avisar (de hoy o atrasados).
  - Alertas de inventario (PB-21): vencidos, agotados, stock crítico (menos de
    2), stock bajo (menos de 5) y por vencer, con lote, fecha y cantidad.

La campana pide este contenido después de cargar la página (fetch), así que
no retrasa ninguna pantalla.
"""

from django.utils import timezone

from .permissions import tiene_rol

ROLES_RECORDATORIOS = ("administrador", "veterinario", "auxiliar", "groomer")
ROLES_INVENTARIO = ("administrador", "veterinario", "auxiliar")

# Cuántos recordatorios se muestran en la campana (el resto, en la pantalla).
MAX_RECORDATORIOS = 5


def _alertas_inventario(hoy):
    # Import local: inventario importa de usuarios al arrancar.
    from apps.inventario.alertas import alertas_inventario

    return alertas_inventario(hoy)


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
