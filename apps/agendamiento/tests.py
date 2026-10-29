from datetime import date, time

from django.test import SimpleTestCase

from . import calendario as cal


def _evento(inicio, fin, categoria=cal.CATEGORIA_CONSULTA, fecha=date(2026, 9, 21)):
    return cal.Evento(
        fecha=fecha, inicio=inicio, fin=fin, titulo="Firulais",
        detalle="", servicio="", categoria=categoria,
    )


class CalendarioHU08Tests(SimpleTestCase):

    def test_categoria_por_tipo_servicio(self):
        self.assertEqual(cal.categoria_de("peluqueria"), cal.CATEGORIA_PELUQUERIA)
        self.assertEqual(cal.categoria_de("vacunacion"), cal.CATEGORIA_CONSULTA)

    def test_inicio_semana_es_lunes(self):
        self.assertEqual(cal.inicio_semana(date(2026, 9, 27)), date(2026, 9, 21))

    def test_posicion_vertical(self):
        e = _evento(time(8, 0), time(9, 0))
        cal.distribuir([e], 7, 20)
        self.assertAlmostEqual(e.top, 100 / 13, places=2)

    def test_citas_solapadas_en_columnas(self):
        a = _evento(time(9, 0), time(10, 0))
        b = _evento(time(9, 30), time(10, 30))
        c = _evento(time(11, 0), time(11, 30))
        cal.distribuir([a, b, c], 7, 20)
        self.assertEqual((a.columna, a.columnas), (0, 2))
        self.assertEqual((b.columna, b.columnas), (1, 2))
        self.assertEqual((c.columna, c.columnas), (0, 1))

    def test_rango_horas_se_amplia(self):
        eventos = [_evento(time(6, 30), time(7, 0)), _evento(time(20, 0), time(20, 45))]
        self.assertEqual(cal.rango_horas(eventos), (6, 21))

    def test_titulo_rango(self):
        semana = [date(2026, 9, 21 + i) for i in range(7)]
        self.assertEqual(cal.titulo_rango("semana", semana), "21 – 27 de septiembre de 2026")



# ──────────────────────────────────────────────────────────────
# RF05 / PB-11 · Cancelación de citas de consulta
# ──────────────────────────────────────────────────────────────
from datetime import timedelta  # noqa: E402

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import TestCase  # noqa: E402
from django.urls import reverse  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.directorio.models import Dueno, Mascota  # noqa: E402
from apps.usuarios.models import Rol  # noqa: E402

from .forms import CitaForm  # noqa: E402
from .models import Cita  # noqa: E402


class CancelarCitaRF05Tests(TestCase):

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        rol_vet = Rol.objects.create(nombre_rol="veterinario")
        rol_rec = Rol.objects.create(nombre_rol="recepcion")
        cls.vet = User.objects.create_user(
            username="vet", password="x", id_rol=rol_vet, nombre_completo="Dra. Vet"
        )
        cls.recep = User.objects.create_user(
            username="recep", password="x", id_rol=rol_rec, nombre_completo="Recepción"
        )
        dueno = Dueno.objects.create(nombre_completo="Ana", telefono="3001112233", direccion="Calle 1")
        cls.mascota = Mascota.objects.create(id_dueno=dueno, nombre="Firulais", especie="perro")
        cls.fecha = timezone.localdate() + timedelta(days=2)

    def setUp(self):
        self.client.force_login(self.recep)
        self.cita = Cita.objects.create(
            mascota=self.mascota, veterinario=self.vet, tipo_servicio="consulta_general",
            fecha=self.fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
        )
        self.url = reverse("agendamiento:cancelar_cita", args=[self.cita.pk])

    def test_cancelar_guarda_estado_y_motivo(self):
        resp = self.client.post(self.url, {"motivo_cancelacion": "  El dueño no puede asistir  "})
        self.assertEqual(resp.status_code, 302)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "cancelada")
        self.assertEqual(self.cita.motivo_cancelacion, "El dueño no puede asistir")

    def test_solo_acepta_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "programada")

    def test_requiere_login(self):
        self.client.logout()
        resp = self.client.post(self.url, {"motivo_cancelacion": "x"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "programada")

    def test_motivo_obligatorio(self):
        self.client.post(self.url, {"motivo_cancelacion": "   "})
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "programada")

    def test_motivo_demasiado_largo(self):
        self.client.post(self.url, {"motivo_cancelacion": "x" * 256})
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "programada")

    def test_no_cancela_cita_atendida(self):
        Cita.objects.filter(pk=self.cita.pk).update(estado="atendida")
        self.client.post(self.url, {"motivo_cancelacion": "x"})
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, "atendida")
        self.assertEqual(self.cita.motivo_cancelacion, "")

    def test_cancelar_dos_veces_conserva_primer_motivo(self):
        self.client.post(self.url, {"motivo_cancelacion": "Primero"})
        self.client.post(self.url, {"motivo_cancelacion": "Segundo"})
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.motivo_cancelacion, "Primero")

    def test_cita_inexistente_404(self):
        url = reverse("agendamiento:cancelar_cita", args=[99999])
        self.assertEqual(self.client.post(url, {"motivo_cancelacion": "x"}).status_code, 404)

    def test_redirige_al_calendario_y_bloquea_next_externo(self):
        resp = self.client.post(self.url, {"motivo_cancelacion": "x", "next": "https://evil.example/"})
        self.assertTrue(resp.url.startswith(reverse("agendamiento:calendario")))
        cita2 = Cita.objects.create(
            mascota=self.mascota, veterinario=self.vet, fecha=self.fecha, hora_inicio=time(10, 0),
        )
        destino = f"{reverse('agendamiento:calendario')}?vista=dia&fecha={self.fecha.isoformat()}"
        resp = self.client.post(
            reverse("agendamiento:cancelar_cita", args=[cita2.pk]),
            {"motivo_cancelacion": "x", "next": destino},
        )
        self.assertEqual(resp.url, destino)

    def test_horario_cancelado_se_puede_volver_a_agendar(self):
        datos = {
            "mascota": self.mascota.pk, "veterinario": self.vet.pk, "tipo_servicio": "consulta_general",
            "fecha": self.fecha.isoformat(), "hora_inicio": "09:00", "hora_fin": "09:30",
        }
        # Antes de cancelar el horario está ocupado
        self.assertFalse(CitaForm(datos).is_valid())
        self.client.post(self.url, {"motivo_cancelacion": "Reprogramada"})
        # Después de cancelar se puede agendar de nuevo en la misma franja
        form = CitaForm(datos)
        self.assertTrue(form.is_valid(), form.errors)
        nueva = form.save()
        self.assertEqual(nueva.estado, "programada")
        self.assertEqual(Cita.objects.filter(veterinario=self.vet, fecha=self.fecha).count(), 2)

    def test_calendario_muestra_cancelada_tachada_con_motivo_y_boton(self):
        url_cal = reverse("agendamiento:calendario") + f"?vista=dia&fecha={self.fecha.isoformat()}"
        html = self.client.get(url_cal).content.decode()
        # Cita programada: ofrece cancelar
        self.assertIn(f'data-cancelar-url="{self.url}"', html)
        self.assertIn('data-cancelable="1"', html)
        self.client.post(self.url, {"motivo_cancelacion": "Motivo visible"})
        html = self.client.get(url_cal).content.decode()
        self.assertIn("cal-event--cancelada", html)
        self.assertIn('data-motivo="Motivo visible"', html)
        self.assertIn('data-cancelable="0"', html)

    def test_evento_cancelable_solo_si_programada(self):
        ev = cal.eventos_desde_citas([self.cita])[0]
        self.assertTrue(ev.cancelable)
        self.cita.estado = "cancelada"
        self.cita.motivo_cancelacion = "x"
        ev = cal.eventos_desde_citas([self.cita])[0]
        self.assertFalse(ev.cancelable)
        self.assertEqual(ev.motivo_cancelacion, "x")
