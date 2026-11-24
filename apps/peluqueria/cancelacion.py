"""
Cancelación de citas de peluquería (PB-11 / RF05).

Una sola regla para todas las pantallas que cancelan (calendario y
Facturación):

- Solo se cancela una cita «Programada»: una ya cancelada o ya realizada
  (cerrada) no cambia.
- El motivo es obligatorio y queda guardado en la cita.
- Al guardar, la señal de peluquería devuelve los insumos al inventario
  (PB-17), y como las citas canceladas no cuentan al revisar cruces de
  horario, la franja queda libre para agendar otra cita.

Quién puede cancelar: el administrador, el auxiliar y el groomer de la cita.
"""

from django.db import transaction

from apps.usuarios.permissions import obtener_rol, tiene_rol

MOTIVO_MAX = 255


class CancelacionNoPermitida(Exception):
    """La cita no se puede cancelar; el mensaje explica por qué."""


def puede_cancelar(usuario, cita):
    """True si el usuario puede cancelar esa cita de peluquería."""
    if tiene_rol(usuario, 'administrador', 'auxiliar'):
        return True
    return (obtener_rol(usuario) == 'groomer'
            and cita.groomer_id is not None and cita.groomer_id == usuario.pk)


def cancelar_cita_peluqueria(cita, motivo):
    """
    Cancela la cita y guarda el motivo. Lanza CancelacionNoPermitida si la
    cita no está programada o si falta el motivo.
    """
    motivo = (motivo or '').strip()
    with transaction.atomic():
        # Se relee bloqueada: dos cancelaciones a la vez no la procesan dos veces.
        actual = type(cita).objects.select_for_update().get(pk=cita.pk)
        if actual.estado == 'Cancelada':
            raise CancelacionNoPermitida('Esta cita ya estaba cancelada.')
        if actual.estado != 'Programada':
            raise CancelacionNoPermitida(
                f'No se puede cancelar una cita que ya está {actual.estado.lower()}.')
        if not motivo:
            raise CancelacionNoPermitida('Debes indicar el motivo de la cancelación.')
        if len(motivo) > MOTIVO_MAX:
            raise CancelacionNoPermitida(f'El motivo no puede superar los {MOTIVO_MAX} caracteres.')

        actual.estado = 'Cancelada'
        actual.motivo_cancelacion = motivo
        actual.save()    # la señal devuelve los insumos al inventario
    cita.estado, cita.motivo_cancelacion = actual.estado, actual.motivo_cancelacion
    return cita
