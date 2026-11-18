"""Confirmación de la cita de peluquería para el cliente (PDF + WhatsApp)."""
from datetime import timedelta
from urllib.parse import unquote

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.directorio.models import Dueno, Mascota
from apps.usuarios.models import Rol, Usuario

from . import confirmacion
from .models import CitaPeluqueria


class ConfirmacionClienteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        rol, _ = Rol.objects.get_or_create(nombre_rol="auxiliar")
        cls.recepcion = Usuario.objects.create_user(username="recep_conf", password="x", id_rol=rol)
        cls.groomer = Usuario.objects.create_user(
            username="groomer_conf", password="x", nombre_completo="Laura Gómez",
            id_rol=Rol.objects.get_or_create(nombre_rol="groomer")[0])
        cls.dueno = Dueno.objects.create(nombre_completo="Carlos Ruiz", telefono="3001234567",
                                         direccion="Calle secreta 123")
        cls.mascota = Mascota.objects.create(id_dueno=cls.dueno, nombre="Toby", especie="perro")

    def _cita(self, **extra):
        datos = dict(mascota=self.mascota, nombre_mascota="Toby", raza="Criollo", servicio="BANO",
                     fecha_hora=timezone.now() + timedelta(days=2), precio=50000, groomer=self.groomer,
                     observaciones="Nota interna: muerde al secar")
        datos.update(extra)
        return CitaPeluqueria.objects.create(**datos)

    def _url(self, cita):
        return reverse("peluqueria:confirmacion_cliente", args=[confirmacion.token_para(cita)])

    def test_el_cliente_abre_el_pdf_sin_iniciar_sesion(self):
        r = self.client.get(self._url(self._cita()))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertIn("inline", r["Content-Disposition"])
        self.assertIn("no-store", r["Cache-Control"])

    def test_el_pdf_lleva_costo_y_mascota_pero_no_datos_internos(self):
        from django.template.loader import render_to_string  # noqa: PLC0415
        cita = self._cita()
        with self.settings(DEBUG=False):
            html = render_to_string("peluqueria/pdf_cliente.html", {
                "cita": cita, "nombre_mascota": "Toby", "dueno_nombre": "Carlos", "groomer_nombre": "Laura",
                "inicio": timezone.localtime(cita.fecha_hora), "llegada": timezone.localtime(cita.fecha_hora),
                "entrega": timezone.localtime(cita.fecha_hora), "duracion_texto": "1 hora",
                "precio_formateado": "$50.000 COP", "codigo_reserva": confirmacion.codigo_reserva(cita),
                "proximo_bano": confirmacion.proximo_bano(cita), "antes_de_venir": confirmacion.ANTES_DE_VENIR,
                "marca": {}, "clinica": {"nombre": "Prados Pets"},
            })
        self.assertIn("Toby", html)
        self.assertIn("Costo total", html)
        self.assertIn("$50.000 COP", html)
        self.assertIn(f"PP-{cita.pk:05d}", html)
        self.assertNotIn("muerde", html)
        self.assertNotIn("Calle secreta", html)
        self.assertNotIn("3001234567", html)

    def test_enlace_alterado_no_muestra_nada(self):
        cita = self._cita()
        token = confirmacion.token_para(cita)
        r = self.client.get(reverse("peluqueria:confirmacion_cliente", args=[token[:-2] + "xx"]))
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "No encontramos esta confirmación", status_code=404)

    def test_cita_cancelada_o_vencida(self):
        r = self.client.get(self._url(self._cita(estado="Cancelada")))
        self.assertContains(r, "Esta cita fue cancelada", status_code=410)
        vieja = self._cita(fecha_hora=timezone.now() - timedelta(days=confirmacion.DIAS_TRAS_LA_CITA + 1))
        self.assertContains(self.client.get(self._url(vieja)), "Este enlace ya venció", status_code=410)

    def test_otras_rutas_siguen_pidiendo_sesion(self):
        cita = self._cita()
        r = self.client.get(reverse("peluqueria:comprobante_pdf", args=[cita.pk]))
        self.assertEqual(r.status_code, 302)

    def test_mensaje_de_whatsapp(self):
        cita = self._cita()
        self.client.force_login(self.recepcion)
        r = self.client.get(reverse("peluqueria:panel_peluqueria"), {"descargar": cita.pk})
        enlace = r.context["whatsapp_cliente"]
        self.assertTrue(enlace.startswith("https://wa.me/573001234567?text="))
        texto = unquote(enlace)
        self.assertIn("¡Hola, Carlos!", texto)
        self.assertIn("*Toby*", texto)
        self.assertIn("Costo total: $50.000 COP", texto)
        self.assertIn(f"/peluqueria/confirmacion/{confirmacion.token_para(cita)}/", texto)
        self.assertContains(r, "Enviar por WhatsApp")
        self.assertContains(r, "Ver PDF del cliente")

    def test_sin_telefono_no_hay_boton_de_whatsapp(self):
        sin_tel = Dueno.objects.create(nombre_completo="Ana", telefono="12", direccion="x")
        cita = self._cita(mascota=Mascota.objects.create(id_dueno=sin_tel, nombre="Luna", especie="gato"))
        self.client.force_login(self.recepcion)
        r = self.client.get(reverse("peluqueria:panel_peluqueria"), {"descargar": cita.pk})
        self.assertEqual(r.context["whatsapp_cliente"], "")
        self.assertContains(r, "no tiene un teléfono válido")

    def test_el_calendario_permite_reenviar_la_confirmacion(self):
        cita = self._cita()
        self.client.force_login(self.recepcion)
        fecha = timezone.localtime(cita.fecha_hora).date().isoformat()
        r = self.client.get(reverse("agendamiento:calendario"), {"vista": "dia", "fecha": fecha})
        self.assertContains(r, 'data-whatsapp="https://wa.me/573001234567')
        self.assertContains(r, "Enviar confirmación por WhatsApp")

    def test_proximo_bano_solo_para_bano(self):
        bano = self._cita(intervalo_recordatorio_dias=30)
        self.assertEqual(confirmacion.proximo_bano(bano),
                         timezone.localdate(bano.fecha_hora) + timedelta(days=30))
        self.assertIsNone(confirmacion.proximo_bano(self._cita(servicio="CORTE")))
