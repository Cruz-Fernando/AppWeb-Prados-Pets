"""
PB-18 / RF15: clasificación por colores de los clientes recurrentes.

Una visita es una consulta atendida (agendamiento.Cita) o una peluquería
realizada (peluqueria.CitaPeluqueria) de cualquier mascota del dueño, dentro
de los últimos VENTANA_MESES meses. Cada cita cuenta como una visita, aunque
el mismo día haya consulta y peluquería.

Dueno guarda el resultado en numero_visitas y es_recurrente:
  - signals.py lo recalcula cuando una cita empieza o deja de contar;
  - el comando `recalcular_visitas` lo recalcula para todos;
  - como la ventana avanza sola con los días (una visita de hace 12 meses
    sale sin que ninguna cita cambie), las pantallas que muestran el nivel
    llaman a refrescar_duenos(), que vuelve a contar y corrige lo guardado.

Para cambiar los criterios del patrocinador basta con tocar las constantes.
"""

import calendar
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, time
from typing import NamedTuple

from django.db.models import Count
from django.utils import timezone

from .models import Dueno, Mascota

# ---------------------------------------------------------------------------
# Criterios del patrocinador
# ---------------------------------------------------------------------------

# Meses hacia atrás (desde hoy) en los que se cuentan las visitas.
VENTANA_MESES = 12

# (desde cuántas visitas, clave, etiqueta, color), de menor a mayor.
# La clave es también la clase CSS: .pp-nivel--<clave> (static/css/styles.css).
NIVELES = (
    (0, 'nuevo', 'Nuevo', 'gris'),
    (2, 'ocasional', 'Ocasional', 'azul'),
    (4, 'frecuente', 'Frecuente', 'verde'),
    (8, 'vip', 'VIP', 'dorado'),
)

# Desde este nivel el dueño queda marcado como recurrente (es_recurrente).
NIVEL_RECURRENTE = 'frecuente'

# Estados que cuentan como visita.
CONSULTA_ATENDIDA = 'atendida'
PELUQUERIA_REALIZADA = 'Realizada'


# ---------------------------------------------------------------------------
# Niveles
# ---------------------------------------------------------------------------

class Nivel(NamedTuple):
    clave: str
    etiqueta: str
    color: str
    minimo: int
    maximo: int | None   # None: sin tope (el último nivel)

    @property
    def rango(self):
        """Ej.: «4 a 7 visitas», «8 o más visitas»."""
        if self.maximo is None:
            return f'{self.minimo} o más visitas'
        if self.minimo == self.maximo:
            return f'{self.minimo} visita{"" if self.minimo == 1 else "s"}'
        return f'{self.minimo} a {self.maximo} visitas'

    @property
    def descripcion(self):
        return f'{self.etiqueta}: {self.rango} en los últimos {VENTANA_MESES} meses'

    def como_dict(self):
        """Lo que recibe el JS de la búsqueda en tiempo real."""
        return {'clave': self.clave, 'etiqueta': self.etiqueta,
                'color': self.color, 'descripcion': self.descripcion}


def _armar_niveles():
    niveles = []
    for i, (minimo, clave, etiqueta, color) in enumerate(NIVELES):
        siguiente = NIVELES[i + 1][0] if i + 1 < len(NIVELES) else None
        niveles.append(Nivel(clave, etiqueta, color, minimo,
                             siguiente - 1 if siguiente is not None else None))
    return tuple(niveles)


TODOS_LOS_NIVELES = _armar_niveles()
NIVEL_POR_CLAVE = {n.clave: n for n in TODOS_LOS_NIVELES}
_MINIMO_RECURRENTE = NIVEL_POR_CLAVE[NIVEL_RECURRENTE].minimo


def nivel_de(visitas):
    """Nivel (clave, etiqueta, color…) que corresponde a un número de visitas."""
    visitas = visitas or 0
    for nivel in reversed(TODOS_LOS_NIVELES):
        if visitas >= nivel.minimo:
            return nivel
    return TODOS_LOS_NIVELES[0]


def es_recurrente(visitas):
    return (visitas or 0) >= _MINIMO_RECURRENTE


# ---------------------------------------------------------------------------
# Conteo de visitas
# ---------------------------------------------------------------------------

def inicio_ventana(hoy=None):
    """Primer día que cuenta: hoy menos VENTANA_MESES meses (29 feb → 28 feb)."""
    hoy = hoy or timezone.localdate()
    meses = hoy.year * 12 + (hoy.month - 1) - VENTANA_MESES
    anio, mes = divmod(meses, 12)
    mes += 1
    return date(anio, mes, min(hoy.day, calendar.monthrange(anio, mes)[1]))


def contar_visitas(dueno_ids=None, hoy=None):
    """
    Visitas de cada dueño dentro de la ventana: {id_dueno: visitas}.

    Es UNA sola consulta (consultas y peluquerías agrupadas por dueño y
    unidas con UNION ALL), sin importar cuántos dueños sean. Con
    dueno_ids=None cuenta a todos. Los dueños sin visitas no aparecen
    en el resultado (valen 0).
    """
    from apps.agendamiento.models import Cita
    from apps.peluqueria.models import CitaPeluqueria

    desde = inicio_ventana(hoy)
    consultas = Cita.objects.filter(estado=CONSULTA_ATENDIDA, fecha__gte=desde)
    peluquerias = CitaPeluqueria.objects.filter(
        estado=PELUQUERIA_REALIZADA,
        mascota__isnull=False,
        fecha_hora__gte=timezone.make_aware(datetime.combine(desde, time.min)),
    )
    if dueno_ids is not None:
        dueno_ids = list(dueno_ids)
        if not dueno_ids:
            return {}
        consultas = consultas.filter(mascota__id_dueno__in=dueno_ids)
        peluquerias = peluquerias.filter(mascota__id_dueno__in=dueno_ids)

    # order_by() vacío: el ordering de los modelos se metería en el GROUP BY
    # y en el ORDER BY del UNION.
    agrupar = lambda qs: qs.order_by().values('mascota__id_dueno').annotate(n=Count('pk'))  # noqa: E731
    visitas = Counter()
    for fila in agrupar(consultas).union(agrupar(peluquerias), all=True).order_by():
        visitas[fila['mascota__id_dueno']] += fila['n']
    return dict(visitas)


def _aplicar(duenos, visitas, guardar=True):
    """Pone los valores calculados en los dueños y guarda solo los que cambiaron."""
    cambiados = []
    for dueno in duenos:
        n = visitas.get(dueno.pk, 0)
        recurrente = es_recurrente(n)
        if dueno.numero_visitas != n or dueno.es_recurrente != recurrente:
            dueno.numero_visitas = n
            dueno.es_recurrente = recurrente
            cambiados.append(dueno)
    if guardar and cambiados:
        Dueno.objects.bulk_update(cambiados, ['numero_visitas', 'es_recurrente'], batch_size=500)
    return cambiados


def refrescar_duenos(duenos, todos=False, hoy=None):
    """
    Para las pantallas: vuelve a contar las visitas de los dueños ya cargados,
    deja los valores al día en esos mismos objetos y corrige en la base los
    que estaban atrasados. Cuesta 1 consulta (+1 si hay algo que corregir).

    todos=True cuando se muestran todos los dueños: cuenta sin filtrar por id.
    """
    duenos = list(duenos)
    if duenos:
        _aplicar(duenos, contar_visitas(None if todos else [d.pk for d in duenos], hoy=hoy))
    return duenos


def actualizar_visitas(duenos=None, guardar=True, hoy=None):
    """
    Recalcula numero_visitas y es_recurrente. duenos: queryset de Dueno
    (None = todos). Devuelve la lista de dueños que cambiaron.
    """
    todos = duenos is None
    lista = list((Dueno.objects.all() if todos else duenos)
                 .only('pk', 'numero_visitas', 'es_recurrente').order_by())
    if not lista:
        return []
    visitas = contar_visitas(None if todos else [d.pk for d in lista], hoy=hoy)
    return _aplicar(lista, visitas, guardar=guardar)


# ---------------------------------------------------------------------------
# Peluquerías antiguas sin mascota vinculada
# ---------------------------------------------------------------------------

def _normalizar(texto):
    """«  Pepín » → «pepin»: sin tildes, sin mayúsculas y sin espacios de más."""
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(texto.casefold().split())


def vincular_peluquerias_sin_mascota(citas=None, guardar=True):
    """
    Las peluquerías antiguas solo guardaban el nombre de la mascota como texto
    y por eso no se podían contar para ningún dueño. Aquí se vinculan a la
    mascota del directorio cuando el nombre (y la raza, si el nombre se repite)
    corresponde a UNA sola mascota. Las que no se pueden resolver se dejan igual.

    citas: lista de CitaPeluqueria a revisar (None = todas las que no tienen mascota).
    Devuelve (vinculadas, sin_resolver): listas de (cita, mascota o None).
    """
    from apps.peluqueria.models import CitaPeluqueria

    if citas is None:
        citas = list(CitaPeluqueria.objects.filter(mascota__isnull=True)
                     .only('pk', 'nombre_mascota', 'raza', 'mascota', 'estado', 'fecha_hora'))
    citas = [c for c in citas if c.mascota_id is None]
    if not citas:
        return [], []

    por_nombre = defaultdict(list)
    for mascota in Mascota.objects.only('pk', 'nombre', 'raza', 'id_dueno'):
        por_nombre[_normalizar(mascota.nombre)].append(mascota)

    vinculadas, sin_resolver = [], []
    for cita in citas:
        candidatas = por_nombre.get(_normalizar(cita.nombre_mascota), [])
        if len(candidatas) > 1:
            raza = _normalizar(cita.raza)
            candidatas = [m for m in candidatas if _normalizar(m.raza) == raza]
        if len(candidatas) == 1:
            cita.mascota = candidatas[0]
            vinculadas.append((cita, candidatas[0]))
        else:
            sin_resolver.append((cita, None))

    if guardar and vinculadas:
        # bulk_update no dispara señales: el recálculo lo hace quien llama.
        CitaPeluqueria.objects.bulk_update([c for c, _ in vinculadas], ['mascota'], batch_size=500)
    return vinculadas, sin_resolver
