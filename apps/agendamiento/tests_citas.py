from datetime import date, time, timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.directorio.models import Dueno, Mascota
from apps.usuarios.models import Rol, Usuario

from .forms import CitaForm
from .models import Cita


class CitasHorarioTests(TestCase):
    def setUp(self):
        rol, _ = Rol.objects.get_or_create(nombre_rol="veterinario")
        self.vet = Usuario.objects.create_user(
            username="vet", password="x", id_rol=rol, nombre_completo="Dra. Vet"
        )
        dueno = Dueno.objects.create(nombre_completo="Ana", telefono="3001234567", direccion="Calle 1")
        self.mascota = Mascota.objects.create(id_dueno=dueno, nombre="Luna", especie="perro")
        self.fecha = timezone.localdate() + timedelta(days=2)

    def _cita(self, inicio, fin=None, **extra):
        return Cita(
            mascota=self.mascota, veterinario=self.vet, fecha=self.fecha,
            hora_inicio=inicio, hora_fin=fin, **extra,
        )

    def test_cita_que_se_cruza_por_rango_se_rechaza(self):
        self._cita(time(10, 0), time(11, 0)).save()
        with self.assertRaises(ValidationError):
            self._cita(time(10, 30), time(11, 30)).full_clean()

    def test_sin_hora_fin_se_asumen_30_minutos(self):
        self._cita(time(10, 0)).save()
        with self.assertRaises(ValidationError):
            self._cita(time(10, 15)).full_clean()
        self._cita(time(10, 30)).full_clean()  # justo cuando termina la otra: permitido

    def test_citas_consecutivas_estan_permitidas(self):
        self._cita(time(10, 0), time(11, 0)).save()
        self._cita(time(11, 0), time(12, 0)).full_clean()

    def test_cita_cancelada_no_bloquea_el_horario(self):
        self._cita(time(10, 0), time(11, 0), estado="cancelada").save()
        self._cita(time(10, 0), time(11, 0)).full_clean()

    def test_hora_fin_debe_ser_posterior_al_inicio(self):
        with self.assertRaises(ValidationError) as ctx:
            self._cita(time(10, 0), time(9, 0)).full_clean()
        self.assertIn("hora_fin", ctx.exception.message_dict)

    def test_editar_una_cita_pasada_ya_no_falla_por_la_fecha(self):
        cita = Cita(
            mascota=self.mascota, veterinario=self.vet,
            fecha=timezone.localdate() - timedelta(days=3), hora_inicio=time(9, 0),
        )
        cita.save()  # save() no valida; simula una cita que ya estaba guardada
        cita.estado = "atendida"
        cita.full_clean()  # no debe lanzar error

    def test_crear_cita_pasada_se_rechaza(self):
        cita = Cita(
            mascota=self.mascota, veterinario=self.vet,
            fecha=timezone.localdate() - timedelta(days=1), hora_inicio=time(9, 0),
        )
        with self.assertRaises(ValidationError):
            cita.full_clean()

    def test_hoy_se_calcula_con_la_zona_horaria_local_no_utc(self):
        """A las 8 p. m. en Bogotá ya es "mañana" en UTC; 'hoy' debe seguir permitido."""
        hoy_local = date(2026, 10, 28)
        with mock.patch("django.utils.timezone.localdate", return_value=hoy_local):
            cita = Cita(
                mascota=self.mascota, veterinario=self.vet,
                fecha=hoy_local, hora_inicio=time(21, 0),
            )
            cita.full_clean()
            form = CitaForm()
            self.assertEqual(form.fields["fecha"].widget.attrs["min"], "2026-10-28")


class AgendarCitaFlujoTests(TestCase):
    def setUp(self):
        rol_v, _ = Rol.objects.get_or_create(nombre_rol="veterinario")
        rol_a, _ = Rol.objects.get_or_create(nombre_rol="auxiliar")
        self.vet = Usuario.objects.create_user(username="vet", password="x", id_rol=rol_v)
        Usuario.objects.create_user(username="aux", password="x", id_rol=rol_a)
        dueno = Dueno.objects.create(nombre_completo="Ana", telefono="3001234567", direccion="Calle 1")
        self.mascota = Mascota.objects.create(id_dueno=dueno, nombre="Luna", especie="perro")
        self.client.login(username="aux", password="x")

    def test_tras_agendar_vuelve_al_formulario_y_ofrece_el_pdf(self):
        fecha = (timezone.localdate() + timedelta(days=1)).isoformat()
        r = self.client.post(reverse("agendamiento:agendar_cita"), {
            "mascota": self.mascota.pk, "veterinario": self.vet.pk,
            "tipo_servicio": "consulta_general", "fecha": fecha, "hora_inicio": "10:00",
        })
        cita = Cita.objects.get()
        self.assertRedirects(
            r, f"{reverse('agendamiento:agendar_cita')}?descargar={cita.pk}",
            fetch_redirect_response=False,
        )
        r = self.client.get(f"{reverse('agendamiento:agendar_cita')}?descargar={cita.pk}")
        self.assertContains(r, reverse("agendamiento:cita_pdf", args=[cita.pk]))
        self.assertContains(r, "Cita agendada")
