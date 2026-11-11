"""
Recordatorios automáticos de vacunación y baño (PB-14 / RF12).

Toma la ÚLTIMA cita de vacunación y la ÚLTIMA cita de baño de cada mascota
(sin contar las canceladas) y calcula cuándo toca el próximo recordatorio
según el intervalo en días que fijó el patrocinador para esa cita.

Lo usan la pantalla Clínico › Recordatorios y el panel principal, para que
los recordatorios del día aparezcan solos al entrar al sistema.
"""

from datetime import timedelta

from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.peluqueria.models import CitaPeluqueria


def fechas_recordatorio(fecha_base, intervalo_dias, hoy):
    """
    Devuelve (fecha_recordatorio, fecha_siguiente).

    Si la cita es de hoy o futura, el recordatorio es esa misma fecha.
    Si ya pasó, se avanza en saltos de `intervalo_dias` hasta llegar a hoy
    o al primer día después de hoy.
    """
    intervalo_dias = max(int(intervalo_dias or 1), 1)
    fecha_recordatorio = fecha_base
    if fecha_recordatorio < hoy:
        dias_transcurridos = (hoy - fecha_recordatorio).days
        ciclos = (dias_transcurridos + intervalo_dias - 1) // intervalo_dias
        fecha_recordatorio += timedelta(days=ciclos * intervalo_dias)
    return fecha_recordatorio, fecha_recordatorio + timedelta(days=intervalo_dias)


def _ultima_por_mascota(citas, fecha_de):
    """De varias citas de la misma mascota se queda con la más reciente."""
    ultimas = {}
    for cita in citas:
        actual = ultimas.get(cita.mascota_id)
        if actual is None or fecha_de(cita) >= fecha_de(actual):
            ultimas[cita.mascota_id] = cita
    return list(ultimas.values())


def calcular_recordatorios(hoy=None):
    """
    Devuelve un dict con:
      - vacunas: lista de recordatorios de vacunación (uno por mascota)
      - banos: lista de recordatorios de baño (uno por mascota)
      - hoy: los recordatorios cuya fecha es hoy (vacunas y baños juntos)
    """
    hoy = hoy or timezone.localdate()

    citas_vacunacion = (
        Cita.objects.select_related("mascota", "mascota__id_dueno")
        .filter(tipo_servicio="vacunacion")
        .exclude(estado="cancelada")
    )
    citas_bano = (
        CitaPeluqueria.objects.select_related("mascota", "mascota__id_dueno")
        .filter(mascota__isnull=False, servicio="BANO")
        .exclude(estado="Cancelada")
    )

    vacunas, banos, de_hoy = [], [], []

    for cita in _ultima_por_mascota(citas_vacunacion, lambda c: (c.fecha, c.hora_inicio)):
        fecha_recordatorio, fecha_siguiente = fechas_recordatorio(
            cita.fecha, cita.intervalo_recordatorio_dias, hoy
        )
        item = {
            "cita_id": cita.pk,
            "mascota": cita.mascota,
            "servicio": cita.get_tipo_servicio_display(),
            "fecha_recordatorio": fecha_recordatorio,
            "fecha_siguiente": fecha_siguiente,
            "intervalo_dias": cita.intervalo_recordatorio_dias,
            "tipo": "Vacunación",
        }
        vacunas.append(item)
        if fecha_recordatorio == hoy:
            de_hoy.append(item)

    for cita in _ultima_por_mascota(citas_bano, lambda c: c.fecha_hora):
        fecha_recordatorio, fecha_siguiente = fechas_recordatorio(
            timezone.localdate(cita.fecha_hora), cita.intervalo_recordatorio_dias, hoy
        )
        item = {
            "cita_id": cita.pk,
            "mascota": cita.mascota,
            "servicio": cita.get_servicio_display(),
            "fecha_recordatorio": fecha_recordatorio,
            "fecha_siguiente": fecha_siguiente,
            "intervalo_dias": cita.intervalo_recordatorio_dias,
            "tipo": "Baño",
        }
        banos.append(item)
        if fecha_recordatorio == hoy:
            de_hoy.append(item)

    vacunas.sort(key=lambda r: r["fecha_recordatorio"])
    banos.sort(key=lambda r: r["fecha_recordatorio"])
    return {"vacunas": vacunas, "banos": banos, "hoy": de_hoy}