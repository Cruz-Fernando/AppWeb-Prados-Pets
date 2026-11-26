"""
PB-18: recalcula numero_visitas y es_recurrente de todos los dueños.

Sirve para llenar los datos que ya existían antes de PB-18 y se puede volver
a correr cuando se quiera (solo guarda lo que cambió). Antes de contar,
vincula las peluquerías antiguas que no tienen mascota cuando el nombre
corresponde a una sola mascota del directorio.

    python manage.py recalcular_visitas            # vincula y recalcula
    python manage.py recalcular_visitas --simular  # muestra qué haría, sin guardar
"""

from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.directorio.models import Dueno
from apps.directorio.recurrencia import (TODOS_LOS_NIVELES, VENTANA_MESES, actualizar_visitas,
                                         nivel_de, vincular_peluquerias_sin_mascota)


class Command(BaseCommand):
    help = (f'Recalcula las visitas de los últimos {VENTANA_MESES} meses y el nivel de '
            'recurrencia de cada dueño (PB-18).')

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true',
                            help='Muestra los cambios sin guardar nada.')
        parser.add_argument('--sin-vincular', action='store_true',
                            help='No intenta vincular las peluquerías antiguas sin mascota.')

    def handle(self, *args, simular=False, sin_vincular=False, **options):
        guardar = not simular
        if simular:
            self.stdout.write(self.style.WARNING('Modo simulación: no se guarda nada.'))

        with transaction.atomic():
            if not sin_vincular:
                self._vincular(guardar)
            cambiados = actualizar_visitas(guardar=guardar)

        verbo = 'cambiarían' if simular else 'actualizados'
        self.stdout.write(f'Dueños {verbo}: {len(cambiados)}')
        for dueno in cambiados[:30]:
            self.stdout.write(f'  · {dueno.pk}: {dueno.numero_visitas} visitas → '
                              f'{nivel_de(dueno.numero_visitas).etiqueta}')
        if len(cambiados) > 30:
            self.stdout.write(f'  … y {len(cambiados) - 30} más')

        if guardar:
            por_nivel = Counter(nivel_de(n).clave for n in
                                Dueno.objects.values_list('numero_visitas', flat=True))
            resumen = ', '.join(f'{n.etiqueta}: {por_nivel.get(n.clave, 0)}' for n in TODOS_LOS_NIVELES)
            self.stdout.write(self.style.SUCCESS(f'Listo. {resumen}'))

    def _vincular(self, guardar):
        vinculadas, sin_resolver = vincular_peluquerias_sin_mascota(guardar=guardar)
        if not vinculadas and not sin_resolver:
            return
        verbo = 'se vincularían' if not guardar else 'vinculadas'
        self.stdout.write(f'Peluquerías antiguas sin mascota {verbo}: {len(vinculadas)}')
        for cita, mascota in vinculadas:
            self.stdout.write(f'  · #{cita.pk} «{cita.nombre_mascota}» → {mascota.nombre} '
                              f'[{mascota.pk}] (dueño {mascota.id_dueno_id})')
        if sin_resolver:
            self.stdout.write(self.style.WARNING(
                f'Sin resolver (ninguna o varias mascotas con ese nombre), quedan igual: {len(sin_resolver)}'))
            for cita, _ in sin_resolver:
                self.stdout.write(f'  · #{cita.pk} «{cita.nombre_mascota}» ({cita.raza})')
