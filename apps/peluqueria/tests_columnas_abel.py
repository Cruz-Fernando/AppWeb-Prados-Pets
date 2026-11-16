"""Las columnas condicion_pelaje y comision_groomer (rama Abel) no rompen el agendado."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.directorio.models import Dueno, Mascota
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol, Usuario


class ColumnasAbelTests(TestCase):
    def setUp(self):
        auxiliar = Usuario.objects.create_user(
            username="aux_pelu", password="Clave#12345", nombre_completo="Auxiliar",
            id_rol=Rol.objects.get_or_create(nombre_rol="auxiliar")[0],
        )
        self.groomer = Usuario.objects.create_user(
            username="groomer_pelu", password="Clave#12345", nombre_completo="Groomer",
            id_rol=Rol.objects.get_or_create(nombre_rol="groomer")[0],
        )
        dueno = Dueno.objects.create(nombre_completo="Ana", telefono="3110000001", direccion="Calle 1")
        self.mascota = Mascota.objects.create(
            id_dueno=dueno, nombre="Luna", especie="perro", sexo="F", peso=12, tamano="mediano",
        )
        self.client.force_login(auxiliar)

    def test_agendar_peluqueria_guarda_y_calcula_comision(self):
        fecha_hora = (timezone.localtime() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        respuesta = self.client.post("/peluqueria/guardar-cita/", {
            "mascota_id": self.mascota.pk, "servicio": "BANO", "groomer_id": self.groomer.pk,
            "fecha_hora": fecha_hora.strftime("%Y-%m-%dT%H:%M"), "duracion_min": "60", "precio": "40000",
            "condicion_pelaje": "Normal",
        })
        self.assertEqual(respuesta.status_code, 302)
        cita = CitaPeluqueria.objects.get()
        self.assertEqual(cita.condicion_pelaje, "Normal")
        self.assertEqual(cita.comision_groomer, Decimal("16000.00"))

    def test_comision_se_actualiza_al_cambiar_precio(self):
        cita = CitaPeluqueria.objects.create(
            mascota=self.mascota, nombre_mascota="Luna", raza="Criollo",
            fecha_hora=timezone.now() + timedelta(days=3), precio=10000,
        )
        cita.precio = 20000
        cita.save(update_fields=["precio"])
        cita.refresh_from_db()
        self.assertEqual(cita.comision_groomer, Decimal("8000.00"))
