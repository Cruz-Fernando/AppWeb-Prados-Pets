"""
Al cancelar una cita de peluquería, sus insumos vuelven al inventario (PB-17).

Se hace con una señal para que funcione venga de donde venga la cancelación
(pantalla de peluquería, calendario o administrador de Django). Es seguro
llamarla varias veces: lo ya devuelto no se devuelve otra vez.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CitaPeluqueria


@receiver(post_save, sender=CitaPeluqueria, dispatch_uid='peluqueria_devolver_insumos_al_cancelar')
def devolver_insumos_al_cancelar(sender, instance, created, raw=False, **kwargs):
    if raw or created or instance.estado != 'Cancelada':
        return
    from .insumos import devolver_insumos_cita
    devolver_insumos_cita(instance)