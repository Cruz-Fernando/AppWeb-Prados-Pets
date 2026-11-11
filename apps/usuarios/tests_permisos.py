"""Pruebas del control de acceso por rol (PB-01 / RF16) usado por los módulos.

Antes, ``rol_requerido`` leía ``request.user.rol`` (no existe) y solo dejaba
pasar al superusuario. Estas pruebas aseguran que se lea ``id_rol.nombre_rol``.
"""
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.http import HttpResponse

from .models import Rol
from .permissions import obtener_rol, rol_requerido, tiene_rol


@rol_requerido("administrador", "veterinario", "recepcionista")
def vista_protegida(request):
    return HttpResponse("ok")


class RolRequeridoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()

        def crear(username, rol):
            return Usuario.objects.create_user(
                username=username,
                password="testpass123",
                nombre_completo=username,
                id_rol=Rol.objects.get_or_create(nombre_rol=rol)[0],
            )

        cls.admin = crear("admin_permiso", "administrador")
        cls.veterinario = crear("vet_permiso", "veterinario")
        cls.auxiliar = crear("aux_permiso", "auxiliar")
        cls.groomer = crear("groomer_permiso", "groomer")

    def _llamar(self, usuario):
        request = RequestFactory().get("/")
        request.user = usuario
        request.session = {}
        request._messages = _MensajesFalsos()
        return vista_protegida(request)

    def test_lee_el_rol_desde_id_rol(self):
        self.assertEqual(obtener_rol(self.veterinario), "veterinario")

    def test_administrador_sin_superusuario_tiene_acceso(self):
        self.assertFalse(self.admin.is_superuser)
        self.assertEqual(self._llamar(self.admin).status_code, 200)

    def test_veterinario_tiene_acceso(self):
        self.assertEqual(self._llamar(self.veterinario).status_code, 200)

    def test_auxiliar_entra_donde_se_pide_recepcionista(self):
        # «recepcionista» no existe como rol; en la clínica es el auxiliar.
        self.assertTrue(tiene_rol(self.auxiliar, "recepcionista"))
        self.assertEqual(self._llamar(self.auxiliar).status_code, 200)

    def test_rol_no_permitido_recibe_403(self):
        self.assertEqual(self._llamar(self.groomer).status_code, 403)

    def test_mayusculas_en_el_nombre_del_rol_no_afectan(self):
        self.assertTrue(tiene_rol(self.admin, "ADMINISTRADOR"))


class _MensajesFalsos:
    """Almacén mínimo para que ``messages.error`` funcione con RequestFactory."""

    def __init__(self):
        self.mensajes = []

    def add(self, level, message, extra_tags=""):
        self.mensajes.append(message)