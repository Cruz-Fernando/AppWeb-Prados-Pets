"""
PB-18: el contador de visitas del dueño se recalcula cuando una consulta o una
peluquería empieza o deja de contar como visita (atendida / realizada,
cancelada, cambiada de mascota o borrada), venga el cambio de donde venga:
agenda, peluquería, facturación o administrador de Django.

Para no gastar consultas de más (cada una cuesta ~150 ms con Supabase), al
cargar una cita se recuerda si contaba como visita; al guardarla solo se
recalcula si contaba antes o cuenta ahora. Crear o reprogramar una cita
programada no cuesta ninguna consulta extra.
"""

from django.db.models import QuerySet
from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

from .models import Dueno, Mascota
from .recurrencia import (CONSULTA_ATENDIDA, PELUQUERIA_REALIZADA, actualizar_visitas,
                          vincular_peluquerias_sin_mascota)

CONSULTA = 'agendamiento.Cita'
PELUQUERIA = 'peluqueria.CitaPeluqueria'
ESTADO_VISITA = {CONSULTA: CONSULTA_ATENDIDA, PELUQUERIA: PELUQUERIA_REALIZADA}


def _cuenta(instance):
    return instance.estado == ESTADO_VISITA[instance._meta.label]


def _recordar(sender, instance, **kwargs):
    # Si «estado» viene diferido (.only/.defer) no se lee: costaría una consulta.
    if 'estado' in instance.__dict__:
        instance._pb18_contaba = _cuenta(instance)
        instance._pb18_mascota = instance.mascota_id
    else:
        instance._pb18_contaba = None   # no se sabe: se recalcula por si acaso


def _recalcular(*mascota_ids):
    ids = {m for m in mascota_ids if m}
    if ids:
        actualizar_visitas(Dueno.objects.filter(mascotas__in=ids).distinct())


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
    if cuenta and instance.mascota_id is None and sender._meta.label == PELUQUERIA:
        # Peluquería antigua sin mascota: se intenta vincular por nombre.
        vincular_peluquerias_sin_mascota([instance])
        instance._pb18_mascota = instance.mascota_id
    _recalcular(instance.mascota_id, mascota_antes)


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
    _recalcular(instance.mascota_id)


@receiver(post_delete, sender=Mascota, dispatch_uid='directorio_pb18_mascota_borrada')
def _mascota_borrada(sender, instance, origin=None, **kwargs):
    if _modelo_origen(origin) is Dueno:
        return   # el dueño también se borró
    actualizar_visitas(Dueno.objects.filter(pk=instance.id_dueno_id))


for _modelo in (CONSULTA, PELUQUERIA):
    _uid = _modelo.replace('.', '_').lower()
    post_init.connect(_recordar, sender=_modelo, dispatch_uid=f'directorio_pb18_init_{_uid}')
    post_save.connect(_guardada, sender=_modelo, dispatch_uid=f'directorio_pb18_save_{_uid}')
    post_delete.connect(_borrada, sender=_modelo, dispatch_uid=f'directorio_pb18_delete_{_uid}')
