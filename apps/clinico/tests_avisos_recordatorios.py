"""Recordatorios más fáciles de usar: «Ya avisé», atrasados, WhatsApp y campana."""
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.directorio.models import Dueno, Mascota
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol

from .models import AvisoRecordatorio
from .recordatorios import DIAS_ATRASO, calcular_recordatorios, describir_intervalo, enlace_whatsapp


class RecordatoriosAvisosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol, _ = Rol.objects.get_or_create(nombre_rol="veterinario")
        cls.vet = get_user_model().objects.create_user(
            username="vet_avisos", password="x", nombre_completo="Dra. Ana", id_rol=rol,
        )
        dueno = Dueno.objects.create(nombre_completo="Carlos Ruiz", telefono="3001234567", direccion="Cúcuta")
        cls.mascota = Mascota.objects.create(id_dueno=dueno, nombre="Toby", especie="perro")

    def setUp(self):
        self.client.force_login(self.vet)
        self.hoy = timezone.localdate()

    def _vacuna(self, dias, intervalo=30):
        return Cita.objects.create(
            mascota=self.mascota, veterinario=self.vet, tipo_servicio="vacunacion",
            fecha=self.hoy + timedelta(days=dias), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            intervalo_recordatorio_dias=intervalo,
        )

    def _avisar(self, cita, fecha, fetch=False, **extra):
        cabeceras = {"HTTP_X_REQUESTED_WITH": "fetch"} if fetch else {}
        return self.client.post(reverse("clinico:recordatorio_avisado"), {
            "tipo_recordatorio": "vacunacion", "cita_id": cita.pk, "fecha": fecha.isoformat(), **extra,
        }, **cabeceras)

    # ---------- Textos ----------
    def test_intervalos_en_palabras(self):
        self.assertEqual(describir_intervalo(365), "1 año")
        self.assertEqual(describir_intervalo(90), "3 meses")
        self.assertEqual(describir_intervalo(14), "2 semanas")
        self.assertEqual(describir_intervalo(10), "10 días")
        self.assertEqual(describir_intervalo(1), "1 día")

    def test_enlace_whatsapp_agrega_indicativo_a_celular_local(self):
        url = enlace_whatsapp("300 123 4567", "Hola")
        self.assertTrue(url.startswith("https://wa.me/573001234567?text=Hola"))
        self.assertEqual(enlace_whatsapp("", "Hola"), "")

    # ---------- Pendientes y atrasados ----------
    def test_recordatorio_de_hoy_queda_pendiente_hasta_marcarlo(self):
        cita = self._vacuna(-30)
        self.assertEqual(len(calcular_recordatorios()["pendientes"]), 1)

        r = self._avisar(cita, self.hoy)
        self.assertRedirects(r, reverse("clinico:recordatorios"))
        self.assertTrue(AvisoRecordatorio.objects.filter(cita_id=cita.pk, fecha_recordatorio=self.hoy).exists())
        datos = calcular_recordatorios()
        self.assertEqual(datos["pendientes"], [])
        self.assertTrue(datos["vacunas"][0]["avisado"])

    def test_recordatorio_sin_avisar_sigue_como_atrasado_unos_dias(self):
        # Tocaba hace 2 días (ciclo de 30): el próximo es en 28 días, pero sigue pendiente.
        self._vacuna(-32)
        recordatorio = calcular_recordatorios()["pendientes"][0]
        self.assertEqual(recordatorio["estado"], "atrasado")
        self.assertEqual(recordatorio["fecha_aviso"], self.hoy - timedelta(days=2))
        self.assertEqual(recordatorio["fecha_recordatorio"], self.hoy + timedelta(days=28))

    def test_atrasado_de_mas_de_una_semana_ya_no_es_pendiente(self):
        self._vacuna(-(30 + DIAS_ATRASO + 1))
        self.assertEqual(calcular_recordatorios()["pendientes"], [])

    def test_deshacer_aviso_y_respuesta_json_para_la_campana(self):
        cita = self._vacuna(-30)
        r = self._avisar(cita, self.hoy, fetch=True)
        self.assertEqual(r.json()["ok"], True)
        r = self._avisar(cita, self.hoy, accion="deshacer")
        self.assertFalse(AvisoRecordatorio.objects.exists())
        self.assertEqual(len(calcular_recordatorios()["pendientes"]), 1)

    def test_aviso_rechaza_datos_invalidos_y_redireccion_externa(self):
        cita = self._vacuna(-30)
        r = self.client.post(reverse("clinico:recordatorio_avisado"),
                             {"tipo_recordatorio": "otro", "cita_id": cita.pk, "fecha": self.hoy.isoformat()})
        self.assertEqual(r.status_code, 400)
        r = self._avisar(cita, self.hoy, next="https://malicioso.example/")
        self.assertRedirects(r, reverse("clinico:recordatorios"))

    def test_groomer_puede_marcar_pero_domiciliario_no(self):
        cita = self._vacuna(-30)
        domi = get_user_model().objects.create_user(
            username="domi_av", password="x", id_rol=Rol.objects.get_or_create(nombre_rol="domiciliario")[0])
        self.client.force_login(domi)
        self.assertEqual(self._avisar(cita, self.hoy).status_code, 403)

    # ---------- Pantalla ----------
    def test_pantalla_muestra_whatsapp_y_boton_ya_avise(self):
        self._vacuna(-30)
        r = self.client.get(reverse("clinico:recordatorios"))
        self.assertContains(r, "https://wa.me/573001234567")
        self.assertContains(r, "Ya avisé")
        self.assertContains(r, "Cada 1 mes")

    def test_mensaje_claro_al_cambiar_el_lapso(self):
        admin = get_user_model().objects.create_user(
            username="admin_av", password="x", id_rol=Rol.objects.get_or_create(nombre_rol="administrador")[0])
        self.client.force_login(admin)
        cita = self._vacuna(5, intervalo=365)
        r = self.client.post(reverse("clinico:recordatorios"), {
            "guardar_intervalo_recordatorio": "1", "tipo_recordatorio": "vacunacion",
            "cita_id": cita.pk, "intervalo_recordatorio_dias": "180",
        }, follow=True)
        self.assertContains(r, "a Toby se le recordará la vacunación cada 6 meses")
        r = self.client.post(reverse("clinico:recordatorios"), {
            "guardar_intervalo_recordatorio": "1", "tipo_recordatorio": "vacunacion",
            "cita_id": cita.pk, "intervalo_recordatorio_dias": "5000",
        }, follow=True)
        self.assertContains(r, "no puede pasar de 10 años")
        cita.refresh_from_db()
        self.assertEqual(cita.intervalo_recordatorio_dias, 180)

    # ---------- Campana ----------
    def test_campana_cuenta_recordatorios_pendientes(self):
        cita = self._vacuna(-30)
        CitaPeluqueria.objects.create(
            mascota=self.mascota, nombre_mascota="Toby", raza="Criollo", servicio="BANO",
            fecha_hora=timezone.now() - timedelta(days=15), intervalo_recordatorio_dias=15,
        )
        r = self.client.get(reverse("usuarios:notificaciones"))
        self.assertEqual(r.context["total_recordatorios"], 2)
        self.assertContains(r, 'data-total="')
        self.assertContains(r, "Avisar a propietarios")

        self._avisar(cita, self.hoy)
        r = self.client.get(reverse("usuarios:notificaciones"))
        self.assertEqual(r.context["total_recordatorios"], 1)

    def test_campana_aparece_en_las_pantallas_internas(self):
        r = self.client.get(reverse("usuarios:dashboard"))
        self.assertContains(r, 'id="notif-boton"')
