from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.directorio.models import Dueno, Mascota
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol

from .models import ConsultaMedica


class HistorialClinicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol = Rol.objects.create(nombre_rol="veterinario")
        cls.profesional = get_user_model().objects.create_user(
            username="veterinaria",
            password="testpass123",
            nombre_completo="Dra. Ana",
            id_rol=rol,
        )
        dueno = Dueno.objects.create(
            nombre_completo="Carlos Ruiz",
            telefono="3001234567",
            direccion="Cúcuta",
        )
        cls.mascota = Mascota.objects.create(
            id_dueno=dueno,
            nombre="Toby",
            especie="perro",
        )

    def setUp(self):
        self.client.force_login(self.profesional)

    def test_lista_mascotas_permite_abrir_historia(self):
        response = self.client.get(
            reverse("clinico:seleccionar_mascota_historial")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecciona una mascota")
        self.assertContains(response, "Toby")
        self.assertContains(
            response,
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota]),
        )

    def test_historial_muestra_formulario_y_estado_vacio(self):
        response = self.client.get(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anamnesis")
        self.assertContains(response, "Constantes vitales")
        self.assertContains(response, "Examen por sistemas")
        self.assertContains(response, "Esta mascota aún no tiene consultas registradas.")

    def test_consulta_se_guarda_en_historial_y_se_muestra(self):
        response = self.client.post(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota]),
            {
                "anamnesis": "Vómito desde ayer y disminución del apetito.",
                "peso": "8.50",
                "temperatura": "38.5",
                "frecuencia_cardiaca": "100",
                "frecuencia_respiratoria": "24",
                "examen_general": "Paciente alerta e hidratado.",
                "sistema_digestivo": "Dolor leve a la palpación abdominal.",
            },
        )

        self.assertRedirects(
            response,
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota]),
        )
        consulta = ConsultaMedica.objects.get(mascota=self.mascota)
        self.assertEqual(consulta.profesional, self.profesional)
        self.assertEqual(consulta.anamnesis, "Vómito desde ayer y disminución del apetito.")
        self.assertEqual(str(consulta.peso), "8.50")
        self.assertEqual(str(consulta.temperatura), "38.5")
        self.assertEqual(consulta.sistema_digestivo, "Dolor leve a la palpación abdominal.")

        historial = self.client.get(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota])
        )
        self.assertContains(historial, "Vómito desde ayer y disminución del apetito.")
        self.assertContains(historial, "38.5 °C")
        self.assertContains(historial, "Dolor leve a la palpación abdominal.")
        self.assertContains(historial, "Dra. Ana")

    def test_consulta_no_se_guarda_sin_anamnesis(self):
        response = self.client.post(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota]),
            {"anamnesis": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("anamnesis", "required"))
        self.assertFalse(ConsultaMedica.objects.exists())

    def test_recordatorios_vacios_sin_citas_de_vacunacion_o_bano(self):
        response = self.client.get(reverse("clinico:recordatorios"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["vacunas_programadas"])
        self.assertFalse(response.context["banos_programados"])
        self.assertContains(response, "No hay recordatorios de vacunación registrados")
        self.assertContains(response, "No hay recordatorios de baño registrados")

    def test_recordatorios_usan_las_fechas_agendadas_en_el_calendario(self):
        hoy = timezone.localdate()
        fecha_vacunacion = hoy + timedelta(days=12)
        Cita.objects.create(
            mascota=self.mascota,
            veterinario=self.profesional,
            tipo_servicio="vacunacion",
            fecha=fecha_vacunacion,
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            intervalo_recordatorio_dias=20,
        )
        fecha_bano = timezone.now() + timedelta(days=7)
        CitaPeluqueria.objects.create(
            mascota=self.mascota,
            nombre_mascota=self.mascota.nombre,
            raza=self.mascota.raza or "No especificada",
            servicio="BANO",
            fecha_hora=fecha_bano,
            intervalo_recordatorio_dias=10,
        )

        response = self.client.get(reverse("clinico:recordatorios"))

        self.assertEqual(response.status_code, 200)
        vacuna = response.context["vacunas_programadas"][0]
        bano = response.context["banos_programados"][0]
        self.assertEqual(vacuna["fecha_recordatorio"], fecha_vacunacion)
        self.assertEqual(vacuna["servicio"], "Vacunación")
        self.assertEqual(vacuna["intervalo_dias"], 20)
        self.assertEqual(vacuna["fecha_siguiente"], fecha_vacunacion + timedelta(days=20))
        self.assertEqual(bano["fecha_recordatorio"], timezone.localdate(fecha_bano))
        self.assertEqual(bano["intervalo_dias"], 10)
        self.assertEqual(
            bano["fecha_siguiente"],
            timezone.localdate(fecha_bano) + timedelta(days=10),
        )
        self.assertEqual(bano["mascota"], self.mascota)
        self.assertContains(response, "Carlos Ruiz")
        self.assertContains(response, "3001234567")
        self.assertContains(response, fecha_vacunacion.strftime("%d/%m/%Y"))

    def test_recordatorios_ignoran_citas_pasadas_canceladas_y_otros_servicios(self):
        hoy = timezone.localdate()
        Cita.objects.create(
            mascota=self.mascota,
            veterinario=self.profesional,
            tipo_servicio="vacunacion",
            fecha=hoy + timedelta(days=3),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            estado="cancelada",
        )
        Cita.objects.create(
            mascota=self.mascota,
            veterinario=self.profesional,
            tipo_servicio="consulta_general",
            fecha=hoy + timedelta(days=4),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
        )
        response = self.client.get(reverse("clinico:recordatorios"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["vacunas_programadas"])
        self.assertFalse(response.context["banos_programados"])

    def test_cita_pasada_se_convierte_en_siguiente_fecha_segun_su_intervalo(self):
        hoy = timezone.localdate()
        Cita.objects.create(
            mascota=self.mascota,
            veterinario=self.profesional,
            tipo_servicio="vacunacion",
            fecha=hoy - timedelta(days=50),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            intervalo_recordatorio_dias=20,
        )

        response = self.client.get(reverse("clinico:recordatorios"))

        self.assertEqual(response.status_code, 200)
        recordatorio = response.context["vacunas_programadas"][0]
        self.assertEqual(
            recordatorio["fecha_recordatorio"],
            hoy + timedelta(days=10),
        )
        self.assertEqual(
            recordatorio["fecha_siguiente"],
            hoy + timedelta(days=30),
        )

    def test_administrador_cambia_intervalo_desde_la_ventana_recordatorios(self):
        admin = get_user_model().objects.create_user(
            username="admin_recordatorios",
            password="testpass123",
            nombre_completo="Administrador",
            id_rol=Rol.objects.create(nombre_rol="administrador"),
        )
        self.client.force_login(admin)
        hoy = timezone.localdate()
        cita_vacuna = Cita.objects.create(
            mascota=self.mascota,
            veterinario=self.profesional,
            tipo_servicio="vacunacion",
            fecha=hoy + timedelta(days=5),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
        )
        cita_bano = CitaPeluqueria.objects.create(
            mascota=self.mascota,
            nombre_mascota=self.mascota.nombre,
            raza=self.mascota.raza or "No especificada",
            servicio="BANO",
            fecha_hora=timezone.now() + timedelta(days=5),
        )

        for tipo, cita_id, intervalo in (
            ("vacunacion", cita_vacuna.pk, "40"),
            ("bano", cita_bano.pk, "15"),
        ):
            response = self.client.post(
                reverse("clinico:recordatorios"),
                {
                    "guardar_intervalo_recordatorio": "1",
                    "tipo_recordatorio": tipo,
                    "cita_id": cita_id,
                    "intervalo_recordatorio_dias": intervalo,
                },
            )
            self.assertRedirects(response, reverse("clinico:recordatorios"))

        cita_vacuna.refresh_from_db()
        cita_bano.refresh_from_db()
        self.assertEqual(cita_vacuna.intervalo_recordatorio_dias, 40)
        self.assertEqual(cita_bano.intervalo_recordatorio_dias, 15)

        response = self.client.get(reverse("clinico:recordatorios"))
        self.assertContains(response, 'name="intervalo_recordatorio_dias" value="40"')
        self.assertContains(response, 'name="intervalo_recordatorio_dias" value="15"')
        self.assertContains(
            response,
            (hoy + timedelta(days=5) + timedelta(days=40)).strftime("%d/%m/%Y"),
        )

    def test_solo_administrador_puede_cambiar_intervalo_desde_recordatorios(self):
        cita = Cita.objects.create(
            mascota=self.mascota,
            veterinario=self.profesional,
            tipo_servicio="vacunacion",
            fecha=timezone.localdate() + timedelta(days=5),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
        )

        response = self.client.post(
            reverse("clinico:recordatorios"),
            {
                "guardar_intervalo_recordatorio": "1",
                "tipo_recordatorio": "vacunacion",
                "cita_id": cita.pk,
                "intervalo_recordatorio_dias": "40",
            },
        )

        self.assertEqual(response.status_code, 403)
        cita.refresh_from_db()
        self.assertEqual(cita.intervalo_recordatorio_dias, 365)

    def test_pantalla_recordatorios_incluye_busqueda_compartida(self):
        fecha = timezone.localdate() + timedelta(days=5)
        Cita.objects.create(
            mascota=self.mascota,
            veterinario=self.profesional,
            tipo_servicio="vacunacion",
            fecha=fecha,
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
        )
        CitaPeluqueria.objects.create(
            mascota=self.mascota,
            nombre_mascota=self.mascota.nombre,
            raza=self.mascota.raza or "No especificada",
            servicio="BANO",
            fecha_hora=timezone.now() + timedelta(days=5),
        )

        response = self.client.get(reverse("clinico:recordatorios"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="buscar-recordatorios"')
        self.assertContains(response, "Mascota, propietario, teléfono o servicio")
        self.assertContains(response, 'data-search="Toby Carlos Ruiz 3001234567 Vacunación"')
        self.assertContains(response, 'data-search="Toby Carlos Ruiz 3001234567 Solamente Baño"')
