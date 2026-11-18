"""
Recordatorios automáticos de vacunación y baño (PB-14 / RF12).

Toma la ÚLTIMA cita de vacunación y la ÚLTIMA cita de baño de cada mascota
(sin contar las canceladas) y calcula cuándo toca el próximo recordatorio
según el intervalo en días que fijó el patrocinador para esa cita.

Lo usan la pantalla Clínico › Recordatorios, el panel principal y la campana
de notificaciones, para que los recordatorios del día aparezcan solos.

Un recordatorio queda «pendiente» el día que le toca y hasta DIAS_ATRASO días
después, mientras nadie lo marque como avisado (modelo AvisoRecordatorio). Así
no se pierde si ese día nadie entró al sistema.
"""

import re
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.peluqueria.models import CitaPeluqueria

from .models import AvisoRecordatorio

# Días que un recordatorio sin avisar sigue apareciendo como «atrasado».
DIAS_ATRASO = 7

# Atajos que se ofrecen al cambiar el lapso de repetición (días, texto).
INTERVALOS_SUGERIDOS = {
    "vacunacion": [(30, "1 mes"), (90, "3 meses"), (180, "6 meses"), (365, "1 año")],
    "bano": [(7, "1 semana"), (15, "15 días"), (30, "1 mes"), (60, "2 meses")],
}

INTERVALO_POR_DEFECTO = {"vacunacion": 365, "bano": 30}


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


def describir_intervalo(dias):
    """365 → «1 año», 90 → «3 meses», 14 → «2 semanas», 10 → «10 días»."""
    dias = int(dias or 0)
    for tamano, singular, plural in ((365, "año", "años"), (30, "mes", "meses"), (7, "semana", "semanas")):
        if dias >= tamano and dias % tamano == 0:
            n = dias // tamano
            return f"{n} {singular if n == 1 else plural}"
    return "1 día" if dias == 1 else f"{dias} días"


def describir_cuando(dias):
    """Días que faltan (negativo si ya pasó) en palabras."""
    if dias == 0:
        return "Hoy"
    if dias == 1:
        return "Mañana"
    if dias == -1:
        return "Ayer"
    return f"En {dias} días" if dias > 0 else f"Hace {-dias} días"


def enlace_whatsapp(telefono, mensaje):
    """Enlace wa.me con el mensaje listo. '' si el teléfono no sirve."""
    digitos = re.sub(r"\D", "", telefono or "")
    if len(digitos) < 7:
        return ""
    # Celular local (10 dígitos) → se antepone el indicativo del país.
    if len(digitos) == 10:
        digitos = getattr(settings, "WHATSAPP_INDICATIVO", "57") + digitos
    return f"https://wa.me/{digitos}?text={quote(mensaje)}"


def _mensaje(tipo, mascota, fecha):
    dueno = getattr(mascota.id_dueno, "nombre_completo", "") or ""
    saludo = f"Hola {dueno.split()[0]}" if dueno.strip() else "Hola"
    servicio = "su vacunación" if tipo == "vacunacion" else "su baño"
    return (
        f"{saludo}, te saludamos de Prados Pets 🐾. Te recordamos que a "
        f"{mascota.nombre} le corresponde {servicio} el {fecha:%d/%m/%Y}. "
        "¿Te agendamos una cita?"
    )


def _ultimas_citas_vacunacion():
    # DISTINCT ON (PostgreSQL): una fila por mascota, la más reciente.
    return (
        Cita.objects.select_related("mascota", "mascota__id_dueno")
        .filter(tipo_servicio="vacunacion")
        .exclude(estado="cancelada")
        .order_by("mascota_id", "-fecha", "-hora_inicio", "-pk")
        .distinct("mascota_id")
    )


def _ultimas_citas_bano():
    return (
        CitaPeluqueria.objects.select_related("mascota", "mascota__id_dueno")
        .filter(mascota__isnull=False, servicio="BANO")
        .exclude(estado="Cancelada")
        .order_by("mascota_id", "-fecha_hora", "-pk")
        .distinct("mascota_id")
    )


def _armar(tipo, cita, fecha_base, servicio, hoy, avisos):
    intervalo = max(int(cita.intervalo_recordatorio_dias or 1), 1)
    fecha_recordatorio, fecha_siguiente = fechas_recordatorio(fecha_base, intervalo, hoy)
    dias = (fecha_recordatorio - hoy).days

    # ¿Qué fecha queda por avisar? La de hoy o, si no, el ciclo anterior
    # cuando pasó hace poco y nadie lo marcó.
    fecha_aviso = None
    if dias == 0:
        fecha_aviso = hoy
    else:
        anterior = fecha_recordatorio - timedelta(days=intervalo)
        if anterior >= fecha_base and (hoy - anterior).days <= DIAS_ATRASO:
            fecha_aviso = anterior
    avisado = fecha_aviso is not None and (tipo, cita.pk, fecha_aviso) in avisos
    pendiente = fecha_aviso is not None and not avisado

    if dias == 0:
        estado = "hoy"
    elif pendiente:
        estado = "atrasado"
    elif dias <= 7:
        estado = "semana"
    else:
        estado = "futuro"

    fecha_mensaje = fecha_aviso or fecha_recordatorio
    return {
        "cita_id": cita.pk,
        "tipo_clave": tipo,
        "mascota": cita.mascota,
        "servicio": servicio,
        "fecha_recordatorio": fecha_recordatorio,
        "fecha_siguiente": fecha_siguiente,
        "intervalo_dias": cita.intervalo_recordatorio_dias,
        "intervalo_texto": describir_intervalo(intervalo),
        "tipo": "Vacunación" if tipo == "vacunacion" else "Baño",
        "dias_restantes": dias,
        "cuando": describir_cuando(dias),
        "estado": estado,
        "fecha_aviso": fecha_aviso,
        "cuando_aviso": describir_cuando((fecha_aviso - hoy).days) if fecha_aviso else "",
        "avisado": avisado,
        "pendiente": pendiente,
        "sugeridos": INTERVALOS_SUGERIDOS[tipo],
        "whatsapp": enlace_whatsapp(
            getattr(cita.mascota.id_dueno, "telefono", ""),
            _mensaje(tipo, cita.mascota, fecha_mensaje),
        ),
    }


def calcular_recordatorios(hoy=None):
    """
    Devuelve un dict con:
      - vacunas: lista de recordatorios de vacunación (uno por mascota)
      - banos: lista de recordatorios de baño (uno por mascota)
      - hoy: los recordatorios cuya fecha es hoy (vacunas y baños juntos)
      - pendientes: los que falta avisar (de hoy o atrasados hasta DIAS_ATRASO)
      - proximos: los de los próximos 7 días (sin contar hoy)
    """
    hoy = hoy or timezone.localdate()
    avisos = set(
        AvisoRecordatorio.objects.filter(fecha_recordatorio__gte=hoy - timedelta(days=DIAS_ATRASO))
        .values_list("tipo", "cita_id", "fecha_recordatorio")
    )

    vacunas = [
        _armar("vacunacion", cita, cita.fecha, cita.get_tipo_servicio_display(), hoy, avisos)
        for cita in _ultimas_citas_vacunacion()
    ]
    banos = [
        _armar("bano", cita, timezone.localdate(cita.fecha_hora), cita.get_servicio_display(), hoy, avisos)
        for cita in _ultimas_citas_bano()
    ]

    vacunas.sort(key=lambda r: r["fecha_recordatorio"])
    banos.sort(key=lambda r: r["fecha_recordatorio"])
    todos = vacunas + banos
    pendientes = sorted((r for r in todos if r["pendiente"]), key=lambda r: r["fecha_aviso"])
    return {
        "vacunas": vacunas,
        "banos": banos,
        "hoy": [r for r in todos if r["dias_restantes"] == 0],
        "pendientes": pendientes,
        "proximos": [r for r in todos if 0 < r["dias_restantes"] <= 7],
    }
