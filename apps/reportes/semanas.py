"""
Semanas del reporte (PB-20).

Cada reporte cubre de domingo a sábado y se genera el SÁBADO: ese día queda
publicado el de la semana que termina. Así cada día pertenece a un solo
reporte, también los domingos.

Entre domingo y viernes el reporte más reciente es el del sábado anterior;
el de la semana en curso aparece cuando llega su sábado.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone

SABADO = 5  # date.weekday(): lunes 0 … sábado 5, domingo 6

DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def sabado_de(fecha):
    """Sábado que cierra la semana (domingo a sábado) a la que pertenece `fecha`."""
    return fecha + timedelta(days=(SABADO - fecha.weekday()) % 7)


def domingo_de(sabado):
    return sabado - timedelta(days=6)


def ultimo_publicado(hoy=None):
    """Sábado del reporte más reciente: hoy si es sábado, si no el sábado anterior."""
    hoy = hoy or timezone.localdate()
    return hoy - timedelta(days=(hoy.weekday() - SABADO) % 7)


def proximo_reporte(hoy=None):
    """Sábado en que se genera el siguiente reporte (el próximo, sin contar hoy)."""
    hoy = hoy or timezone.localdate()
    return ultimo_publicado(hoy) + timedelta(days=7)


def disponibles(cantidad=12, hoy=None):
    """Sábados con reporte publicado, del más reciente al más antiguo."""
    ultimo = ultimo_publicado(hoy)
    return [ultimo - timedelta(weeks=i) for i in range(cantidad)]


def es_publicado(sabado, hoy=None):
    hoy = hoy or timezone.localdate()
    return sabado.weekday() == SABADO and sabado <= hoy


def dias_de(sabado):
    """Las 7 fechas de la semana, de domingo a sábado."""
    domingo = domingo_de(sabado)
    return [domingo + timedelta(days=i) for i in range(7)]


def hora_texto(h):
    """15 → «3 p. m.», 12 → «12 m.», 9 → «9 a. m.»."""
    if h == 12:
        return "12 m."
    return f"{h - 12 if h > 12 else h} {'p. m.' if h > 12 else 'a. m.'}"


def limites(desde, hasta):
    """Datetimes con zona horaria [inicio, fin) para filtrar campos DateTime entre dos fechas incluidas."""
    zona = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(desde, time.min), zona)
    fin = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), zona)
    return inicio, fin
