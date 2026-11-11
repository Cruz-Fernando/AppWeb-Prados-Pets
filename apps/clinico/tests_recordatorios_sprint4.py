"""Pruebas de cierre del Sprint 4 en recordatorios (PB-14 / RF12)."""
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.directorio.models import Dueno, Mascota
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol


class RecordatoriosCierreSprint4Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol, _ = Rol.objects.get_or_create(nombre_rol="veterinario")
        cls.vet = get_user_model().objects.create_user(
            username="vet_s4", password="x", nombre_completo="Dra. Ana", id_rol=rol,
        )
        dueno = Dueno.objects.create(nombre_completo="Carlos", telefono="3001234567", direccion="Cúcuta")
        cls.mascota = Mascota.objects.create(id_dueno=dueno, nombre="Toby", especie="perro")

    def setUp(self):
        self.client.force_login(self.vet)

    def _vacuna(self, dias, intervalo=30, hora=9):
        return Cita.objects.create(
            mascota=self.mascota, veterinario=self.vet, tipo_servicio="vacunacion",
            fecha=timezone.localdate() + timedelta(days=dias),
            hora_inicio=time(hora, 0), hora_fin=time(hora, 30),
            intervalo_recordatorio_dias=intervalo,
        )

    def test_una_mascota_con_varias_vacunas_genera_un_solo_recordatorio(self):
        self._vacuna(-60)
        ultima = self._vacuna(-30, hora=10)
        response = self.client.get(reverse("clinico:recordatorios"))
        vacunas = response.context["vacunas_programadas"]
        self.assertEqual(len(vacunas), 1)
        self.assertEqual(vacunas[0]["cita_id"], ultima.pk)

    def test_bano_cancelado_no_genera_recordatorio(self):
        CitaPeluqueria.objects.create(
            mascota=self.mascota, nombre_mascota="Toby", raza="Criollo",
            servicio="BANO", fecha_hora=timezone.now() + timedelta(days=2), estado="Cancelada",
        )
        response = self.client.get(reverse("clinico:recordatorios"))
        self.assertFalse(response.context["banos_programados"])

    def test_el_panel_muestra_los_recordatorios_de_hoy(self):
        self._vacuna(-30, intervalo=30)          # el ciclo cae justo hoy
        response = self.client.get(reverse("usuarios:dashboard"))
        self.assertContains(response, "Recordatorios de hoy (1)")
        self.assertContains(response, "Toby")

    def test_el_menu_tiene_el_enlace_a_recordatorios(self):
        response = self.client.get(reverse("usuarios:dashboard"))
        self.assertContains(response, 'id="nav-recordatorios"')