"""
HU08: Calendario Visual Semanal y Diario (RF26).

Reúne las citas de consulta médica (agendamiento.Cita) y las de peluquería
(peluqueria.CitaPeluqueria) en una sola estructura para pintarlas en un
calendario diario o semanal, diferenciadas por color según el servicio.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from django.utils import timezone

HORA_INICIO_DEFECTO = 7   # 7:00 a. m.
HORA_FIN_DEFECTO = 20     # 8:00 p. m.
DURACION_DEFECTO_MIN = 30

CATEGORIA_CONSULTA = "consulta"
CATEGORIA_PELUQUERIA = "peluqueria"

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_SEMANA_CORTO = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


@dataclass
class Evento:
    fecha: date
    inicio: time
    fin: time
    titulo: str
    detalle: str
    servicio: str
    categoria: str
    estado: str = "programada"
    responsable: str = ""     # "Dra. X" (consulta) o "Raza: Y" (peluquería)
    # Calculados al distribuir en la grilla
    top: float = 0.0
    alto: float = 0.0
    columna: int = 0
    columnas: int = 1

    @property
    def minuto_inicio(self):
        return self.inicio.hour * 60 + self.inicio.minute

    @property
    def minuto_fin(self):
        return self.fin.hour * 60 + self.fin.minute

    @property
    def izquierda(self):
        return round(100 * self.columna / self.columnas, 3)

    @property
    def ancho(self):
        return round(100 / self.columnas, 3)

    @property
    def cancelada(self):
        return self.estado == "cancelada"

    @property
    def estado_display(self):
        return self.estado.capitalize()

    @property
    def duracion_min(self):
        return self.minuto_fin - self.minuto_inicio


@dataclass
class Dia:
    fecha: date
    eventos: list = field(default_factory=list)

    @property
    def nombre(self):
        return DIAS_SEMANA[self.fecha.weekday()]

    @property
    def nombre_corto(self):
        return DIAS_SEMANA_CORTO[self.fecha.weekday()]

    @property
    def es_hoy(self):
        return self.fecha == timezone.localdate()

    @property
    def total_activas(self):
        return sum(1 for e in self.eventos if not e.cancelada)


def _sumar_minutos(hora, minutos):
    base = datetime.combine(date.min, hora) + timedelta(minutes=minutos)
    if base.date() != date.min:  # se pasó de medianoche
        return time(23, 59)
    return base.time()


def categoria_de(tipo_servicio):
    return CATEGORIA_PELUQUERIA if tipo_servicio == "peluqueria" else CATEGORIA_CONSULTA


def eventos_desde_citas(citas):
    """Convierte citas médicas (agendamiento.Cita) en eventos."""
    eventos = []
    for c in citas:
        fin = c.hora_fin if c.hora_fin and c.hora_fin > c.hora_inicio else _sumar_minutos(
            c.hora_inicio, DURACION_DEFECTO_MIN
        )
        vet = c.veterinario
        nombre_vet = getattr(vet, "nombre_completo", "") or vet.get_username()
        eventos.append(Evento(
            fecha=c.fecha,
            inicio=c.hora_inicio,
            fin=fin,
            titulo=c.mascota.nombre,
            detalle=f"{c.get_tipo_servicio_display()} · {nombre_vet}",
            servicio=c.get_tipo_servicio_display(),
            categoria=categoria_de(c.tipo_servicio),
            estado=c.estado,
            responsable=nombre_vet,
        ))
    return eventos


def eventos_desde_peluqueria(citas):
    """Convierte citas de peluquería (peluqueria.CitaPeluqueria) en eventos."""
    eventos = []
    for c in citas:
        if not c.fecha_hora:
            continue
        dt = c.fecha_hora
        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
        duracion = c.duracion_estimada_min or DURACION_DEFECTO_MIN
        eventos.append(Evento(
            fecha=dt.date(),
            inicio=dt.time().replace(second=0, microsecond=0),
            fin=_sumar_minutos(dt.time(), duracion),
            titulo=c.nombre_mascota,
            detalle=f"{c.get_servicio_display()} · {c.raza}",
            servicio=c.get_servicio_display(),
            categoria=CATEGORIA_PELUQUERIA,
            responsable=f"Raza: {c.raza}",
        ))
    return eventos


def rango_horas(eventos):
    """Horas visibles en la grilla: 7–20 por defecto, ampliadas si hay citas fuera."""
    inicio, fin = HORA_INICIO_DEFECTO, HORA_FIN_DEFECTO
    for e in eventos:
        inicio = min(inicio, e.inicio.hour)
        fin = max(fin, e.fin.hour + (1 if e.fin.minute else 0))
    return inicio, min(fin, 24)


def distribuir(eventos, hora_inicio, hora_fin):
    """
    Calcula posición vertical (top/alto en %) y columnas para citas que se
    cruzan en el mismo día, de modo que no se tapen entre sí.
    """
    total_min = (hora_fin - hora_inicio) * 60
    base = hora_inicio * 60
    eventos = sorted(eventos, key=lambda e: (e.minuto_inicio, e.minuto_fin))

    grupo, fin_grupo = [], -1
    for e in eventos + [None]:
        if e is None or (grupo and e.minuto_inicio >= fin_grupo):
            # Cerrar grupo de citas solapadas
            n = max((g.columna for g in grupo), default=-1) + 1
            for g in grupo:
                g.columnas = n
            grupo, fin_grupo = [], -1
        if e is None:
            break

        ocupadas = {g.columna for g in grupo if g.minuto_fin > e.minuto_inicio}
        col = 0
        while col in ocupadas:
            col += 1
        e.columna = col
        grupo.append(e)
        fin_grupo = max(fin_grupo, e.minuto_fin)

        duracion = max(e.minuto_fin - e.minuto_inicio, 15)
        e.top = round(100 * (e.minuto_inicio - base) / total_min, 3)
        e.alto = round(100 * duracion / total_min, 3)
    return eventos


def construir_dias(eventos, fechas, hora_inicio, hora_fin):
    por_fecha = {f: [] for f in fechas}
    for e in eventos:
        if e.fecha in por_fecha:
            por_fecha[e.fecha].append(e)
    return [Dia(fecha=f, eventos=distribuir(por_fecha[f], hora_inicio, hora_fin)) for f in fechas]


def inicio_semana(d):
    return d - timedelta(days=d.weekday())


def titulo_rango(vista, fechas):
    if vista == "dia":
        d = fechas[0]
        return f"{DIAS_SEMANA[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"
    a, b = fechas[0], fechas[-1]
    if a.month == b.month:
        return f"{a.day} – {b.day} de {MESES[b.month - 1]} de {b.year}"
    if a.year == b.year:
        return f"{a.day} de {MESES[a.month - 1]} – {b.day} de {MESES[b.month - 1]} de {b.year}"
    return f"{a.day} de {MESES[a.month - 1]} de {a.year} – {b.day} de {MESES[b.month - 1]} de {b.year}"
