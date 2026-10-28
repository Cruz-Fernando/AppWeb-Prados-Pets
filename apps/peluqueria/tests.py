from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.directorio.models import Dueno, Mascota
from apps.usuarios.models import Rol, Usuario

from .models import CitaPeluqueria


def _usuario(username, rol):
    rol_obj, _ = Rol.objects.get_or_create(nombre_rol=rol)
    return Usuario.objects.create_user(
        username=username, password="Clave-segura-123", id_rol=rol_obj,
        nombre_completo=username.title(),
    )


class GuardarCitaPeluqueriaTests(TestCase):
    def setUp(self):
        self.recepcion = _usuario("recep", "auxiliar")
        self.groomer = _usuario("groomer1", "groomer")
        self.groomer2 = _usuario("groomer2", "groomer")
        self.vet = _usuario("vet1", "veterinario")
        dueno = Dueno.objects.create(nombre_completo="Ana", telefono="3001234567", direccion="Calle 1")
        self.mascota = Mascota.objects.create(
            id_dueno=dueno, nombre="Luna", especie="perro", tamano="grande"
        )
        self.client.login(username="recep", password="Clave-segura-123")
        self.manana = (timezone.localtime() + timedelta(days=1)).replace(hour=10, minute=0)

    def _datos(self, **cambios):
        datos = {
            "mascota_id": self.mascota.id_mascota,
            "servicio": "BANO",
            "groomer_id": self.groomer.pk,
            "fecha_hora": self.manana.strftime("%Y-%m-%dT%H:%M"),
            "precio": "$50.000 COP",
            "observaciones": "",
        }
        datos.update(cambios)
        return datos

    def _mensajes(self, r):
        return [str(m) for m in get_messages(r.wsgi_request)]

    def test_guarda_cita_con_precio_mascota_y_duracion_segun_tamano(self):
        r = self.client.post(reverse("peluqueria:guardar_cita"), self._datos())
        cita = CitaPeluqueria.objects.get()
        self.assertRedirects(
            r, f"{reverse('peluqueria:panel_peluqueria')}?descargar={cita.pk}",
            fetch_redirect_response=False,
        )
        self.assertEqual(cita.precio, 50000)
        self.assertEqual(cita.mascota, self.mascota)
        self.assertEqual(cita.duracion_estimada_min, 120)  # tamaño grande
        self.assertTrue(timezone.is_aware(cita.fecha_hora))

    def test_comprobante_pdf(self):
        self.client.post(reverse("peluqueria:guardar_cita"), self._datos())
        cita = CitaPeluqueria.objects.get()
        r = self.client.get(reverse("peluqueria:comprobante_pdf", args=[cita.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")

    def test_panel_con_descargar_expone_la_url_del_pdf(self):
        self.client.post(reverse("peluqueria:guardar_cita"), self._datos())
        cita = CitaPeluqueria.objects.get()
        r = self.client.get(reverse("peluqueria:panel_peluqueria"), {"descargar": cita.pk})
        self.assertContains(r, reverse("peluqueria:comprobante_pdf", args=[cita.pk]))

    def test_fecha_vacia_o_invalida_no_rompe_con_500(self):
        for valor in ("", "no-es-fecha"):
            r = self.client.post(reverse("peluqueria:guardar_cita"), self._datos(fecha_hora=valor))
            self.assertEqual(r.status_code, 302)
        self.assertEqual(CitaPeluqueria.objects.count(), 0)

    def test_servicio_ausente_o_invalido_se_rechaza(self):
        for valor in (None, "", "MASAJE"):
            datos = self._datos()
            if valor is None:
                datos.pop("servicio")
            else:
                datos["servicio"] = valor
            r = self.client.post(reverse("peluqueria:guardar_cita"), datos)
            self.assertEqual(r.status_code, 302)
        self.assertEqual(CitaPeluqueria.objects.count(), 0)

    def test_no_permite_fechas_pasadas(self):
        ayer = (timezone.localtime() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        r = self.client.post(reverse("peluqueria:guardar_cita"), self._datos(fecha_hora=ayer))
        self.assertEqual(CitaPeluqueria.objects.count(), 0)
        self.assertTrue(any("pasadas" in m for m in self._mensajes(r)))

    def test_precio_vacio_o_cero_se_rechaza(self):
        for valor in ("$", "", "$0 COP", "abc"):
            self.client.post(reverse("peluqueria:guardar_cita"), self._datos(precio=valor))
        self.assertEqual(CitaPeluqueria.objects.count(), 0)

    def test_groomer_debe_tener_rol_groomer(self):
        self.client.post(reverse("peluqueria:guardar_cita"), self._datos(groomer_id=self.vet.pk))
        self.assertEqual(CitaPeluqueria.objects.count(), 0)

    def test_groomer_no_puede_tener_dos_citas_cruzadas(self):
        self.client.post(reverse("peluqueria:guardar_cita"), self._datos())
        # 10:30, mismo groomer: se cruza con la cita de 10:00–12:00
        cruzada = (self.manana + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M")
        self.client.post(reverse("peluqueria:guardar_cita"), self._datos(fecha_hora=cruzada))
        self.assertEqual(CitaPeluqueria.objects.count(), 1)
        # otro groomer, misma hora: sí se permite
        self.client.post(
            reverse("peluqueria:guardar_cita"),
            self._datos(fecha_hora=cruzada, groomer_id=self.groomer2.pk),
        )
        self.assertEqual(CitaPeluqueria.objects.count(), 2)
        # mismo groomer, justo cuando termina la anterior (12:00): permitido
        despues = (self.manana + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
        self.client.post(reverse("peluqueria:guardar_cita"), self._datos(fecha_hora=despues))
        self.assertEqual(CitaPeluqueria.objects.count(), 3)

    def test_errores_conservan_lo_escrito(self):
        r = self.client.post(reverse("peluqueria:guardar_cita"), self._datos(precio="$"))
        r = self.client.get(reverse("peluqueria:panel_peluqueria"))
        self.assertContains(r, 'id="borrador-datos"')
        # y se consume una sola vez
        r = self.client.get(reverse("peluqueria:panel_peluqueria"))
        self.assertNotContains(r, 'id="borrador-datos"')

    def test_get_a_guardar_cita_redirige(self):
        r = self.client.get(reverse("peluqueria:guardar_cita"))
        self.assertEqual(r.status_code, 302)
