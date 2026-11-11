"""El servidor revisa los datos del propietario aunque el navegador no lo haga."""

from django.test import TestCase

from apps.directorio.models import Dueno
from apps.usuarios.models import Rol, Usuario


class ValidacionDuenoTests(TestCase):
    def setUp(self):
        rol, _ = Rol.objects.get_or_create(nombre_rol="auxiliar")
        usuario = Usuario.objects.create_user(
            username="aux_validacion", password="Clave#12345",
            nombre_completo="Auxiliar Prueba", id_rol=rol,
        )
        self.client.force_login(usuario)
        self.url = "/directorio/registrar-dueno/"
        self.validos = {
            "nombre": "Carlos Ruiz", "telefono": "300 123-4567",
            "direccion": "Av 0 # 1-2", "correo": "carlos@correo.co",
        }

    def test_guarda_y_limpia_el_telefono(self):
        respuesta = self.client.post(self.url, self.validos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Dueno.objects.get().telefono, "3001234567")

    def test_rechaza_nombre_vacio(self):
        respuesta = self.client.post(self.url, {**self.validos, "nombre": "  "})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "El nombre del propietario es obligatorio.")
        self.assertEqual(Dueno.objects.count(), 0)

    def test_rechaza_telefono_con_letras(self):
        respuesta = self.client.post(self.url, {**self.validos, "telefono": "abc"})
        self.assertContains(respuesta, "solo debe tener números")
        self.assertEqual(Dueno.objects.count(), 0)

    def test_rechaza_direccion_vacia_y_correo_malo(self):
        respuesta = self.client.post(self.url, {**self.validos, "direccion": "", "correo": "no-es-correo"})
        self.assertContains(respuesta, "La dirección es obligatoria.")
        self.assertContains(respuesta, "El correo no es válido.")
        self.assertEqual(Dueno.objects.count(), 0)

    def test_editar_tambien_valida(self):
        dueno = Dueno.objects.create(nombre_completo="Ana", telefono="3110000000", direccion="Calle 1")
        self.client.post(f"/directorio/duenos/{dueno.pk}/editar/", {**self.validos, "nombre": ""})
        dueno.refresh_from_db()
        self.assertEqual(dueno.nombre_completo, "Ana")