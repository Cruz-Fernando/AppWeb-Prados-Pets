"""
PB-18: el contador de visitas del dueño se recalcula cuando una consulta o una
peluquería empieza o deja de contar como visita (atendida / realizada,
cancelada, cambiada de mascota o borrada), venga el cambio de donde venga:
agenda, peluquería, facturación o administrador de Django.

Para no gastar consultas de más (cada una cuesta ~150 ms con Supabase):
  - al cargar una cita se recuerda si contaba como visita; al guardarla solo
    se recalcula si contaba antes o cuenta ahora. Crear o reprogramar una cita
    programada no cuesta ninguna consulta extra;
  - el recálculo se hace UNA vez, cuando se confirma la transacción, con todos
    los dueños tocados juntos. Al cobrar una factura con varias citas del mismo
    dueño se cuenta una sola vez, y como se cuenta lo ya confirmado, dos cobros
    al mismo tiempo no se pisan el contador.

Aquí no se vinculan peluquerías sin mascota: eso solo lo hace el comando
recalcular_visitas, que se corre a propósito.
"""

import threading

from django.db import transaction
from django.db.models import QuerySet
from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

from .models import Dueno, Mascota
from .recurrencia import CONSULTA_ATENDIDA, PELUQUERIA_REALIZADA, actualizar_visitas

CONSULTA = 'agendamiento.Cita'
PELUQUERIA = 'peluqueria.CitaPeluqueria'
ESTADO_VISITA = {CONSULTA: CONSULTA_ATENDIDA, PELUQUERIA: PELUQUERIA_REALIZADA}

# Mascotas cuyos dueños hay que recalcular al confirmar la transacción (por hilo:
# cada petición de Gunicorn va en el suyo).
_pendientes = threading.local()


def _programar(*mascota_ids):
    """Anota las mascotas y pide recalcular a sus dueños al confirmar la transacción.
    Fuera de una transacción, on_commit ejecuta el recálculo en el acto."""
    ids = {m for m in mascota_ids if m}
    if not ids:
        return
    if getattr(_pendientes, 'mascotas', None) is None:
        _pendientes.mascotas = set()
    _pendientes.mascotas |= ids
    transaction.on_commit(_recalcular_pendientes)


def _recalcular_pendientes():
    # El primer aviso de la transacción recalcula todo lo anotado; los demás
    # encuentran la lista vacía y no hacen nada. Si una transacción se revierte,
    # lo que anotó se recalcula con la siguiente (contar de nuevo no daña nada).
    ids, _pendientes.mascotas = getattr(_pendientes, 'mascotas', None), None
    if ids:
        actualizar_visitas(Dueno.objects.filter(mascotas__in=ids).distinct())


def _cuenta(instance):
    return instance.estado == ESTADO_VISITA[instance._meta.label]


def _recordar(sender, instance, **kwargs):
    # Si «estado» viene diferido (.only/.defer) no se lee: costaría una consulta.
    if 'estado' in instance.__dict__:
        instance._pb18_contaba = _cuenta(instance)
        instance._pb18_mascota = instance.mascota_id
    else:
        instance._pb18_contaba = None   # no se sabe: se recalcula por si acaso


def _guardada(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    cuenta = _cuenta(instance)
    contaba = getattr(instance, '_pb18_contaba', None)
    mascota_antes = getattr(instance, '_pb18_mascota', None)
    # Lo que quedó guardado es lo «anterior» para el próximo save().
    instance._pb18_contaba, instance._pb18_mascota = cuenta, instance.mascota_id

    if not cuenta and contaba is False:
        return
    _programar(instance.mascota_id, mascota_antes)


def _modelo_origen(origin):
    """Modelo con el que empezó el borrado (un objeto o un queryset)."""
    return origin.model if isinstance(origin, QuerySet) else type(origin)


def _borrada(sender, instance, origin=None, **kwargs):
    # Si se borró la mascota o el dueño, las citas caen en cascada: lo
    # resuelve _mascota_borrada una sola vez en vez de una vez por cita.
    if _modelo_origen(origin) in (Mascota, Dueno):
        return
    if getattr(instance, '_pb18_contaba', None) is False:
        return
    _programar(instance.mascota_id)


@receiver(post_delete, sender=Mascota, dispatch_uid='directorio_pb18_mascota_borrada')
def _mascota_borrada(sender, instance, origin=None, **kwargs):
    if _modelo_origen(origin) is Dueno:
        return   # el dueño también se borró
    # La mascota ya no existe: se recalcula al dueño directamente.
    transaction.on_commit(lambda: actualizar_visitas(Dueno.objects.filter(pk=instance.id_dueno_id)))


for _modelo in (CONSULTA, PELUQUERIA):
    _uid = _modelo.replace('.', '_').lower()
    post_init.connect(_recordar, sender=_modelo, dispatch_uid=f'directorio_pb18_init_{_uid}')
    post_save.connect(_guardada, sender=_modelo, dispatch_uid=f'directorio_pb18_save_{_uid}')
    post_delete.connect(_borrada, sender=_modelo, dispatch_uid=f'directorio_pb18_delete_{_uid}')
