"""
Ganancias por groomer (PB-16: comisión del 40 %; PB-20: comisiones por groomer).

Cada cita de peluquería del periodo se clasifica así:
  - GANADO:     estado «Realizada». Es lo que cuenta para pagar la comisión.
  - POR CERRAR: estado «Programada» con fecha ya pasada. El servicio debió
                prestarse; falta marcarlo como Realizada o Cancelada.
  - AGENDADO:   estado «Programada» con fecha futura (proyección).
  - Las canceladas no suman.

La comisión es la que guarda la cita (40 % del precio); si una cita antigua
no la tiene, se calcula con el mismo 40 %.
"""

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.peluqueria.models import COMISION_GROOMER_PORCENTAJE, CitaPeluqueria

PERIODOS = [
    ('hoy', 'Hoy'),
    ('semana', 'Esta semana'),
    ('mes', 'Este mes'),
    ('mes_anterior', 'Mes anterior'),
    ('rango', 'Elegir fechas'),
]


def rango_de(periodo, desde=None, hasta=None, hoy=None):
    """Devuelve (desde, hasta) como fechas, ambos incluidos."""
    hoy = hoy or timezone.localdate()
    if periodo == 'hoy':
        return hoy, hoy
    if periodo == 'mes':
        return hoy.replace(day=1), hoy
    if periodo == 'mes_anterior':
        fin = hoy.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin
    if periodo == 'rango' and desde and hasta:
        return (desde, hasta) if desde <= hasta else (hasta, desde)
    # Por defecto: la semana en curso, de lunes a domingo
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes, lunes + timedelta(days=6)


def comision_de(cita):
    if cita.comision_groomer and cita.comision_groomer > 0:
        return Decimal(cita.comision_groomer)
    return (Decimal(cita.precio or 0) * COMISION_GROOMER_PORCENTAJE).quantize(Decimal('0.01'))


def clasificar(cita, ahora=None):
    ahora = ahora or timezone.now()
    if cita.estado == 'Realizada':
        return 'ganado'
    if cita.estado == 'Cancelada':
        return 'cancelado'
    return 'por_cerrar' if cita.fecha_hora <= ahora else 'agendado'


@dataclass
class Fila:
    """Totales de un groomer (o de «Sin groomer asignado») en el periodo."""
    groomer: object
    nombre: str
    servicios: int = 0
    facturado: Decimal = Decimal('0')
    comision: Decimal = Decimal('0')
    por_cerrar: int = 0
    por_cerrar_valor: Decimal = Decimal('0')
    agendados: int = 0
    agendado_comision: Decimal = Decimal('0')
    cancelados: int = 0

    @property
    def clinica(self):
        """Lo que le queda a la clínica de lo ganado."""
        return self.facturado - self.comision


@dataclass
class Resumen:
    desde: object
    hasta: object
    filas: list = field(default_factory=list)
    citas: list = field(default_factory=list)

    def _suma(self, atributo):
        return sum((getattr(f, atributo) for f in self.filas), type(getattr(Fila(None, ''), atributo))())

    @property
    def servicios(self):
        return self._suma('servicios')

    @property
    def facturado(self):
        return self._suma('facturado')

    @property
    def comision(self):
        return self._suma('comision')

    @property
    def clinica(self):
        return self.facturado - self.comision

    @property
    def por_cerrar(self):
        return self._suma('por_cerrar')

    @property
    def agendados(self):
        return self._suma('agendados')


def resumen(desde, hasta, groomer=None, ahora=None):
    """Totales por groomer y lista de citas entre dos fechas (incluidas)."""
    ahora = ahora or timezone.now()
    zona = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(desde, time.min), zona)
    fin = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), zona)

    citas = (CitaPeluqueria.objects.filter(fecha_hora__gte=inicio, fecha_hora__lt=fin)
             .select_related('groomer', 'mascota').order_by('fecha_hora', 'pk'))
    if groomer is not None:
        citas = citas.filter(groomer=groomer)

    filas = {}
    lista = []
    for cita in citas:
        clave = cita.groomer_id or 0
        if clave not in filas:
            nombre = (cita.groomer.nombre_completo or cita.groomer.username) if cita.groomer else 'Sin groomer asignado'
            filas[clave] = Fila(groomer=cita.groomer, nombre=nombre)
        fila = filas[clave]
        cita.estado_cobro = clasificar(cita, ahora)
        cita.comision_calculada = comision_de(cita)
        precio = Decimal(cita.precio or 0)
        if cita.estado_cobro == 'ganado':
            fila.servicios += 1
            fila.facturado += precio
            fila.comision += cita.comision_calculada
        elif cita.estado_cobro == 'por_cerrar':
            fila.por_cerrar += 1
            fila.por_cerrar_valor += precio
        elif cita.estado_cobro == 'agendado':
            fila.agendados += 1
            fila.agendado_comision += cita.comision_calculada
        else:
            fila.cancelados += 1
        lista.append(cita)

    ordenadas = sorted(filas.values(), key=lambda f: (f.groomer is None, -f.comision, f.nombre.lower()))
    return Resumen(desde=desde, hasta=hasta, filas=ordenadas, citas=lista)