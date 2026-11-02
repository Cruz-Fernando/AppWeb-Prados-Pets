from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.directorio.models import Dueno, Mascota
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.models import Rol

from .models import Hospitalizacion, RegistroClinico, TrazaClinica


class HistorialClinicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol, _ = Rol.objects.get_or_create(nombre_rol="veterinario")
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

    def _url_nuevo(self, tipo):
        return reverse("clinico:nuevo_registro", args=[self.mascota.id_mascota, tipo])

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

    def test_historial_muestra_tipos_de_registro_y_estado_vacio(self):
        response = self.client.get(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota])
        )

        self.assertEqual(response.status_code, 200)
        for nombre in ("Consulta General", "Vacunación", "Desparasitación", "Sedación",
                       "Cirugía", "Eutanasia", "Control Post-Operatorio", "Otro procedimiento"):
            self.assertContains(response, nombre)
        self.assertNotContains(response, "Peluquería / Spa")
        self.assertContains(response, "Esta mascota aún no tiene consultas registradas.")

    def test_consulta_general_se_guarda_con_examen_por_sistemas_y_traza(self):
        response = self.client.post(self._url_nuevo("consulta_general"), {
            "fecha_atencion": "2026-11-02T09:30",
            "motivo": "Vómito desde ayer",
            "anamnesis": "Vómito desde ayer y disminución del apetito.",
            "peso": "8.50",
            "temperatura": "38.5",
            "frecuencia_cardiaca": "100",
            "d_sistema_digestivo": "Dolor leve a la palpación abdominal.",
            "d_pronostico": "favorable",
        })

        registro = RegistroClinico.objects.get(mascota=self.mascota)
        self.assertRedirects(response, reverse("clinico:registro_detalle", args=[registro.pk]))
        self.assertEqual(registro.tipo, "consulta_general")
        self.assertEqual(registro.profesional, self.profesional)
        self.assertEqual(str(registro.temperatura), "38.5")
        self.assertEqual(registro.detalle["sistema_digestivo"], "Dolor leve a la palpación abdominal.")
        self.assertTrue(TrazaClinica.objects.filter(registro=registro, accion="crear").exists())

        historial = self.client.get(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota])
        )
        self.assertContains(historial, "Vómito desde ayer")
        self.assertContains(historial, "38,5 °C")  # formato es-co
        self.assertContains(historial, "Dra. Ana")

        detalle = self.client.get(reverse("clinico:registro_detalle", args=[registro.pk]))
        self.assertContains(detalle, "Dolor leve a la palpación abdominal.")
        self.assertContains(detalle, "Favorable")

    def test_vacunacion_exige_vacuna_y_lote(self):
        response = self.client.post(self._url_nuevo("vacunacion"), {
            "fecha_atencion": "2026-11-02T09:30",
            "motivo": "Plan vacunal",
            "d_dosis": "1",
            "d_via": "SC",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("d_vacuna", "required"))
        self.assertTrue(response.context["form"].has_error("d_lote", "required"))
        self.assertFalse(RegistroClinico.objects.exists())

    def test_vacunacion_muestra_proxima_dosis_en_proximos_eventos(self):
        proxima = (timezone.localdate() + timedelta(days=21)).isoformat()
        self.client.post(self._url_nuevo("vacunacion"), {
            "fecha_atencion": "2026-11-02T09:30",
            "motivo": "Plan vacunal cachorro",
            "d_vacuna": "Polivalente DHPPi+L",
            "d_lote": "A123",
            "d_dosis": "1",
            "d_via": "SC",
            "d_proxima_dosis": proxima,
        })
        registro = RegistroClinico.objects.get()
        self.assertEqual(registro.detalle["proxima_dosis"], proxima)
        historial = self.client.get(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota])
        )
        self.assertContains(historial, "Vacuna: Polivalente DHPPi+L")

    def test_cirugia_exige_consentimiento(self):
        response = self.client.post(self._url_nuevo("cirugia"), {
            "fecha_atencion": "2026-11-02T09:30",
            "motivo": "Esterilización",
            "d_procedimiento": "Ovariohisterectomía",
            "d_caracter": "electiva",
            "d_asa": "I",
            "d_tecnica": "Abordaje por línea media.",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].has_error("d_consentimiento_firmado", "required"))

    def test_eutanasia_cierra_hospitalizacion_activa(self):
        hosp = Hospitalizacion.objects.create(mascota=self.mascota, motivo="Insuficiencia renal")
        self.client.post(self._url_nuevo("eutanasia"), {
            "fecha_atencion": "2026-11-02T09:30",
            "motivo": "Insuficiencia renal terminal",
            "d_diagnostico_base": "ERC estadio IV",
            "d_consentimiento_firmado": "on",
            "d_autorizado_por": "Carlos Ruiz",
            "d_documento_autorizante": "1090000000",
            "d_sedacion_previa": "Propofol",
            "d_agente": "Pentobarbital 100 mg/kg IV",
            "d_hora_fallecimiento": "09:45",
            "d_confirmacion": "Asistolia y apnea",
            "d_disposicion": "cremacion_individual",
        })
        hosp.refresh_from_db()
        self.assertEqual(hosp.estado, "ALTA")
        self.assertEqual(hosp.condicion_alta, "fallecido")
        historial = self.client.get(
            reverse("clinico:historial_clinico", args=[self.mascota.id_mascota])
        )
        self.assertContains(historial, "Paciente fallecido")

    def test_editar_registro_guarda_diferencias_en_trazabilidad(self):
        registro = RegistroClinico.objects.create(
            mascota=self.mascota, tipo="otro", profesional=self.profesional,
            motivo="Curación", detalle={"procedimiento": "Curación de herida"},
        )
        self.client.post(reverse("clinico:editar_registro", args=[registro.pk]), {
            "fecha_atencion": "2026-11-02T09:30",
            "motivo": "Curación de herida en miembro",
            "d_procedimiento": "Curación de herida",
            "temperatura": "39.0",
        })
        traza = TrazaClinica.objects.get(registro=registro, accion="editar")
        self.assertIn("Temperatura (°C)", traza.cambios)
        self.assertEqual(traza.cambios["Motivo de la atención"], ["Curación", "Curación de herida en miembro"])

    def test_anular_registro_lo_conserva_con_motivo(self):
        registro = RegistroClinico.objects.create(
            mascota=self.mascota, tipo="otro", profesional=self.profesional, motivo="Error",
        )
        self.client.post(reverse("clinico:anular_registro", args=[registro.pk]),
                         {"motivo_anulacion": "Mascota equivocada"})
        registro.refresh_from_db()
        self.assertTrue(registro.anulado)
        self.assertEqual(registro.motivo_anulacion, "Mascota equivocada")
        self.assertTrue(TrazaClinica.objects.filter(registro=registro, accion="anular").exists())

    def test_pdfs_de_registro_e_historia(self):
        registro = RegistroClinico.objects.create(
            mascota=self.mascota, tipo="desparasitacion", profesional=self.profesional,
            motivo="Plan", detalle={"producto": "Drontal", "dosis": "1 tableta",
                                    "tipo_desparasitacion": "interna", "via": "VO"},
        )
        for url in (reverse("clinico:registro_pdf", args=[registro.pk]),
                    reverse("clinico:historia_pdf", args=[self.mascota.id_mascota])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(TrazaClinica.objects.filter(accion="pdf").count(), 2)

    def test_flujo_hospitalizacion_ingreso_evolucion_alta(self):
        response = self.client.get(reverse("clinico:hospitalizacion"))
        self.assertContains(response, "No hay pacientes hospitalizados")

        response = self.client.post(reverse("clinico:ingresar_paciente"), {
            "mascota": self.mascota.id_mascota,
            "motivo": "Gastroenteritis",
            "temperatura": "39.8",
        })
        hosp = Hospitalizacion.objects.get()
        self.assertRedirects(response, reverse("clinico:hospitalizacion_detalle", args=[hosp.pk]))
        self.assertEqual(hosp.profesional_ingreso, self.profesional)

        self.client.post(reverse("clinico:hospitalizacion_detalle", args=[hosp.pk]), {
            "fecha": "2026-11-02T14:00",
            "estado_general": "mejorando",
            "temperatura": "38.9",
            "medicamentos": "Maropitant 1 mg/kg SC",
        })
        self.assertEqual(hosp.evoluciones.count(), 1)

        self.client.post(reverse("clinico:dar_alta", args=[hosp.pk]), {
            "condicion_alta": "mejorado",
            "resumen_alta": "Respondió a fluidoterapia.",
        })
        hosp.refresh_from_db()
        self.assertEqual(hosp.estado, "ALTA")
        self.assertIsNotNone(hosp.fecha_alta)

        pdf = self.client.get(reverse("clinico:hospitalizacion_pdf", args=[hosp.pk]))
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        acciones = set(TrazaClinica.objects.filter(mascota=self.mascota).values_list("accion", flat=True))
        self.assertTrue({"ingreso", "evolucion", "alta", "pdf"} <= acciones)

    def test_rol_sin_permiso_no_puede_registrar(self):
        rol, _ = Rol.objects.get_or_create(nombre_rol="groomer")
        groomer = get_user_model().objects.create_user(
            username="groomer1", password="x", nombre_completo="Groomer", id_rol=rol,
        )
        self.client.force_login(groomer)
        response = self.client.get(self._url_nuevo("consulta_general"))
        self.assertEqual(response.status_code, 403)

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
            hoy,
        )
        self.assertEqual(
            recordatorio["fecha_siguiente"],
            hoy + timedelta(days=20),
        )
        self.assertEqual(response.context["recordatorios_hoy"], [recordatorio])
        self.assertContains(response, 'id="reminder-modal"')

    def test_modal_avisa_vacuna_y_bano_cuando_intervalo_cae_hoy(self):
        hoy = timezone.localdate()
        intervalo_vacuna = 45
        intervalo_bano = 12
        Cita.objects.create(
            mascota=self.mascota,
            veterinario=self.profesional,
            tipo_servicio="vacunacion",
            fecha=hoy - timedelta(days=intervalo_vacuna),
            hora_inicio=time(9, 0),
            hora_fin=time(9, 30),
            intervalo_recordatorio_dias=intervalo_vacuna,
        )
        CitaPeluqueria.objects.create(
            mascota=self.mascota,
            nombre_mascota=self.mascota.nombre,
            raza=self.mascota.raza or "No especificada",
            servicio="BANO",
            fecha_hora=timezone.now() - timedelta(days=intervalo_bano),
            intervalo_recordatorio_dias=intervalo_bano,
        )

        response = self.client.get(reverse("clinico:recordatorios"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["recordatorios_hoy"]), 2)
        self.assertContains(response, "Recordatorios para hoy")
        self.assertContains(response, "Vacunación")
        self.assertContains(response, "Baño")
        self.assertContains(response, "Carlos Ruiz")

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
